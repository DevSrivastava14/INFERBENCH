"""One live workload-sensitivity run of gemma3:1b.

This file is not a pytest module. It stores four profiles, then writes
findings only from the rows loaded back out of SQLite. It does not download
a model, and it does not recommend a profile.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import asyncio
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.benchmark.runner import BenchmarkRunner
from app.benchmark.workload import PROFILES
from app.core.config import OllamaConfig
from app.core.exceptions import OllamaError
from app.database.models import Base
from app.database.repository import StoredExperiment, load_experiment, save_experiment
from app.inference.ollama import OllamaAdapter
from app.metrics.statistics import summarize
from app.monitoring.sampler import ResourceSample, psutil_probe, read_sample
from app.monitoring.snapshot import build_snapshot, psutil_hardware_probe

MODEL = "gemma3:1b"
ENGINE_NAME = "ollama"
WARMUP_COUNT = 2
MEASURED_COUNT = 3
CONCURRENCY = 1
SAMPLE_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 120.0

DB_PATH = ROOT / "experiments" / "results" / "workload-sensitivity.sqlite"
FINDINGS_PATH = ROOT / "docs" / "workload-findings.md"


def main() -> int:
    """Run the four profiles. Return 0 when the findings file is written."""
    config = OllamaConfig.from_env()
    if config.timeout_seconds != TIMEOUT_SECONDS:
        print("refusing to change the adapter timeout", file=sys.stderr)
        return 1
    try:
        asyncio.run(_run(config))
    except OllamaError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


async def _run(config: OllamaConfig) -> None:
    adapter = OllamaAdapter(config)
    await adapter.show_model(MODEL)
    runner = BenchmarkRunner(adapter, clock=time.perf_counter)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if FINDINGS_PATH.exists():
        FINDINGS_PATH.unlink()
    if DB_PATH.exists():
        DB_PATH.unlink()
    engine = create_engine("sqlite:///" + DB_PATH.resolve().as_posix())
    Base.metadata.create_all(engine)
    experiment_ids: list[int] = []
    with Session(engine) as session:
        for profile in PROFILES:
            print(f"running {profile.name}", flush=True)
            await adapter.show_model(MODEL)
            version = await adapter.engine_version()
            snapshot = build_snapshot(
                model=MODEL,
                prompt=profile.prompt,
                num_predict=profile.num_predict,
                warmup_count=WARMUP_COUNT,
                measured_count=MEASURED_COUNT,
                concurrency=CONCURRENCY,
                engine_name=ENGINE_NAME,
                engine_version=version,
                clock=time.perf_counter,
                probe=psutil_hardware_probe,
                profile_name=profile.name,
            )
            run = await runner.run(
                MODEL,
                profile.prompt,
                num_predict=profile.num_predict,
                warmup_count=WARMUP_COUNT,
                measured_count=MEASURED_COUNT,
                concurrency=CONCURRENCY,
                profile_name=profile.name,
                sampler=_sample,
                sample_interval=SAMPLE_INTERVAL_SECONDS,
            )
            summary = summarize(run)
            experiment_ids.append(save_experiment(session, run, snapshot, summary))
            session.commit()
        loaded = tuple(load_experiment(session, experiment_id) for experiment_id in experiment_ids)
    text = _findings(loaded)
    FINDINGS_PATH.write_text(text, encoding="utf-8")
    with Session(engine) as session:
        reread = tuple(load_experiment(session, experiment_id) for experiment_id in experiment_ids)
    if _findings(reread) != text:
        raise RuntimeError("findings text does not match the stored experiments")


def _sample() -> ResourceSample:
    """One real sample. The first CPU reading may be 0. That 0 is kept."""
    return read_sample(psutil_probe, time.perf_counter)


def _findings(experiments: tuple[StoredExperiment, ...]) -> str:
    """Render the note from loaded experiments. Unset fields stay unset."""
    lines = [
        "# Workload sensitivity findings",
        "",
        "These figures were loaded from `experiments/results/workload-sensitivity.sqlite`.",
        "This file describes the four stored summaries.",
        "It does not recommend a profile, and it does not call one configuration an improvement.",
        "",
        "The request timeout was the adapter default of 120 seconds.",
        "The measured count is 3.",
        "A timeout or other adapter error is listed as the stored `error_type`.",
        "It was not retried.",
        "Character length is the length of the stored prompt.",
        "`prompt_eval_count` is the prompt length.",
        "`eval_count` is the output length.",
        "`num_predict` is the cap.",
        "A longer cap is not proof the model emitted that many tokens.",
        "A system CPU sample of 0 stays in the series.",
        "It is a sample value.",
        "",
    ]
    for stored in experiments:
        lines.extend(_profile_lines(stored))
    return "\n".join(lines) + "\n"


def _profile_lines(stored: StoredExperiment) -> list[str]:
    snapshot = stored.snapshot
    summary = stored.summary
    successes = sum(1 for row in stored.measured if row.success)
    cpu_values = tuple(sample.cpu_percent for sample in stored.resource_samples)
    ram_values = tuple(sample.system_ram_used_bytes for sample in stored.resource_samples)
    error_values = [
        f"{row.phase} {row.error_type}"
        for row in (*stored.warmup, *stored.measured)
        if row.error_type is not None
    ]
    name = _show(snapshot.profile_name)
    lines = [
        f"## {name}",
        "",
        f"- Profile name: {name}",
        f"- Model: {_show(snapshot.model)}",
        f"- Engine version: {_show(snapshot.engine_version)}",
        f"- Character length: {len(snapshot.prompt)}",
        f"- num_predict: {_show(snapshot.num_predict)}",
        f"- Measured success count: {successes}",
    ]
    for index, row in enumerate(stored.measured, start=1):
        lines.append(
            f"- Measured row {index}: prompt_eval_count {_show(row.prompt_eval_count)}, "
            f"eval_count {_show(row.eval_count)}, error_type {_show(row.error_type)}"
        )
    lines.extend(
        [
            f"- Average: {_show(summary.average_ms)}",
            f"- Median: {_show(summary.median_ms)}",
            f"- P50: {_show(summary.p50_ms)}",
            f"- P95: {_show(summary.p95_ms)}",
            f"- P99: {_show(summary.p99_ms)}",
            f"- Generation throughput: {_show(summary.generation_throughput_tps)}",
            f"- Request throughput: {_show(summary.request_throughput_rps)}",
            f"- Error rate: {_show(summary.error_rate)}",
            f"- Sample count: {len(stored.resource_samples)}",
            f"- Min system CPU percent: {_show(min(cpu_values) if cpu_values else None)}",
            f"- Max system CPU percent: {_show(max(cpu_values) if cpu_values else None)}",
            f"- Min system RAM used: {_show(min(ram_values) if ram_values else None)}",
            f"- Max system RAM used: {_show(max(ram_values) if ram_values else None)}",
            "- Stored error_type values: " + (", ".join(error_values) if error_values else "none"),
            "",
        ]
    )
    return lines


def _show(value: object) -> str:
    """Format one stored field. None stays unset."""
    if value is None:
        return "unset"
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
