"""Ten live serving-configuration runs.

This file is not a pytest module. It stores five runs of gemma3:1b on
short_prompt_short_output with think omitted, then the same five on
qwen3.5:2b with think false. Runs 1–3 change concurrency and omit
num_thread. Runs 4–5 stay at concurrency 1 and set num_thread. Findings
are written only from the rows loaded back out of SQLite. It does not
download a model, it does not send think true, and it does not recommend
a setting.
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
from app.inference.base import ModelInfo
from app.inference.ollama import OllamaAdapter
from app.metrics.latency import tpot_ms, ttft_ms
from app.metrics.statistics import summarize
from app.monitoring.sampler import ResourceSample, psutil_probe, read_sample
from app.monitoring.snapshot import build_snapshot, psutil_hardware_probe

GEMMA = "gemma3:1b"
QWEN = "qwen3.5:2b"
MODELS: tuple[tuple[str, bool | None], ...] = (
    (GEMMA, None),
    (QWEN, False),
)
PROFILE_NAME = "short_prompt_short_output"
ENGINE_NAME = "ollama"
WARMUP_COUNT = 2
MEASURED_COUNT = 3
LOW_THREAD = 4
MINIMUM_LOGICAL_CPUS = 12
SAMPLE_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 120.0

DB_PATH = ROOT / "experiments" / "results" / "serving-config.sqlite"
FINDINGS_PATH = ROOT / "docs" / "serving-findings.md"


class LogicalCpuStop(Exception):
    """The hardware probe reported fewer than 12 logical CPUs."""

    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(f"logical CPU count {count} is under 12")


def main() -> int:
    """Run both models. Return 0 when the findings file is written."""
    config = OllamaConfig.from_env()
    if config.timeout_seconds != TIMEOUT_SECONDS:
        print("refusing to change the adapter timeout", file=sys.stderr)
        return 1
    try:
        asyncio.run(_run(config))
    except LogicalCpuStop as exc:
        print(
            f"stopping before generate: logical CPU count {exc.count} is under 12",
            file=sys.stderr,
        )
        return 1
    except OllamaError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


async def _run(config: OllamaConfig) -> None:
    profile = next(item for item in PROFILES if item.name == PROFILE_NAME)
    adapter = OllamaAdapter(config)
    shown = {model: await adapter.show_model(model) for model, _think in MODELS}
    listed = await adapter.list_models()
    tags = {model.name: model for model in listed}
    hardware = psutil_hardware_probe()
    if hardware.logical_cpu_count < MINIMUM_LOGICAL_CPUS:
        raise LogicalCpuStop(hardware.logical_cpu_count)
    high_thread = hardware.logical_cpu_count
    runs: tuple[tuple[int, int | None], ...] = (
        (1, None),
        (2, None),
        (4, None),
        (1, LOW_THREAD),
        (1, high_thread),
    )
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
        for model, think in MODELS:
            fields = _metadata(shown[model], tags.get(model))
            for concurrency, num_thread in runs:
                label = "omitted" if num_thread is None else str(num_thread)
                think_label = "omitted" if think is None else "false"
                print(
                    f"running {model} concurrency {concurrency} "
                    f"num_thread {label} think {think_label}",
                    flush=True,
                )
                version = await adapter.engine_version()
                snapshot = build_snapshot(
                    model=model,
                    prompt=profile.prompt,
                    num_predict=profile.num_predict,
                    warmup_count=WARMUP_COUNT,
                    measured_count=MEASURED_COUNT,
                    concurrency=concurrency,
                    engine_name=ENGINE_NAME,
                    engine_version=version,
                    clock=time.perf_counter,
                    probe=psutil_hardware_probe,
                    profile_name=profile.name,
                    think=think,
                    num_thread=num_thread,
                    quantization=fields.quantization,
                    parameter_size=fields.parameter_size,
                    model_size_bytes=fields.size,
                    architecture=fields.architecture,
                )
                run = await runner.run(
                    model,
                    profile.prompt,
                    num_predict=profile.num_predict,
                    warmup_count=WARMUP_COUNT,
                    measured_count=MEASURED_COUNT,
                    concurrency=concurrency,
                    profile_name=profile.name,
                    think=think,
                    num_thread=num_thread,
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


def _metadata(shown: ModelInfo, tag: ModelInfo | None) -> ModelInfo:
    """Copy show fields, and fill a gap from the tags entry.

    The show payload omits size. Tags carry size. A field both omit stays
    unset. This does not invent a label, and it does not generate.
    """

    return ModelInfo(
        name=shown.name,
        size=_filled(shown.size, None if tag is None else tag.size),
        quantization=_filled(shown.quantization, None if tag is None else tag.quantization),
        parameter_size=_filled(
            shown.parameter_size,
            None if tag is None else tag.parameter_size,
        ),
        raw=shown.raw,
        architecture=_filled(shown.architecture, None if tag is None else tag.architecture),
    )


def _filled(primary: object, fallback: object) -> object:
    if primary is not None:
        return primary
    return fallback


def _sample() -> ResourceSample:
    """One real sample. The first CPU reading may be 0. That 0 is kept."""
    return read_sample(psutil_probe, time.perf_counter)


def _findings(experiments: tuple[StoredExperiment, ...]) -> str:
    """Render the note from loaded experiments. Unset fields stay unset."""
    lines = [
        "# Serving configuration findings",
        "",
        "These figures were loaded from `experiments/results/serving-config.sqlite`.",
        "This file describes the ten stored summaries.",
        "It does not recommend a setting.",
        "It does not recommend a thread count or a concurrency cap.",
        "It does not call one configuration an improvement.",
        "",
        "The request timeout was the adapter default of 120 seconds.",
        "The measured count is 3.",
        "Gemma's request does not send think.",
        "Qwen was run with think false.",
        "Thinking was not turned on.",
        "Concurrency 8 and `num_ctx` were not varied.",
        "A timeout or other adapter error is listed as the stored `error_type`.",
        "It was not retried.",
        "Character length is the length of the stored prompt.",
        "`prompt_eval_count` is the prompt length.",
        "`eval_count` is the output length.",
        "`num_predict` is the cap.",
        "The cap is not a token count.",
        "TTFT is `ttft_ms` on the loaded row.",
        "TPOT is `tpot_ms` on the loaded row.",
        "A system CPU sample of 0 stays in the series.",
        "It is a sample value.",
        "",
    ]
    for stored in experiments:
        lines.extend(_run_lines(stored))
    return "\n".join(lines) + "\n"


def _run_lines(stored: StoredExperiment) -> list[str]:
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
    model = _show(snapshot.model)
    thread = _thread(snapshot.num_thread)
    lines = [
        f"## {model} / {name} / concurrency {snapshot.concurrency} / num_thread {thread}",
        "",
        f"- Model: {model}",
        f"- Profile name: {name}",
        f"- Concurrency: {snapshot.concurrency}",
        f"- num_thread: {thread}",
        f"- Think: {_think(snapshot.think)}",
        f"- Quantization: {_show(snapshot.quantization)}",
        f"- Parameter size: {_show(snapshot.parameter_size)}",
        f"- Size in bytes: {_show(snapshot.model_size_bytes)}",
        f"- Architecture: {_architecture(snapshot.architecture)}",
        f"- Engine version: {_show(snapshot.engine_version)}",
        f"- Logical CPU count: {_show(snapshot.logical_cpu_count)}",
        f"- Character length: {len(snapshot.prompt)}",
        f"- num_predict: {_show(snapshot.num_predict)}",
        f"- Measured success count: {successes}",
    ]
    for index, row in enumerate(stored.measured, start=1):
        lines.append(
            f"- Measured row {index}: prompt_eval_count {_show(row.prompt_eval_count)}, "
            f"eval_count {_show(row.eval_count)}, "
            f"TTFT {_show(ttft_ms(row))}, "
            f"TPOT {_show(tpot_ms(row))}, "
            f"error_type {_show(row.error_type)}"
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


def _thread(value: int | None) -> str:
    """An omitted thread value is omitted. It is not the integer 0."""
    if value is None:
        return "omitted"
    return str(value)


def _think(value: bool | None) -> str:
    """The stored flag. An omitted flag stays unset."""
    if value is None:
        return "unset"
    if value is False:
        return "false"
    return "true"


def _architecture(value: str | None) -> str:
    """A missing architecture field is not present."""
    if value is None:
        return "not present"
    return value


def _show(value: object) -> str:
    """Format one stored field. None stays unset."""
    if value is None:
        return "unset"
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
