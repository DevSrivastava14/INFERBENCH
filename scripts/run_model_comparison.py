"""Eight live model-comparison runs.

This file is not a pytest module. It stores four profiles on qwen3.5:2b
with think false, then the same four on gemma3:1b with think omitted.
Findings are written only from the rows loaded back out of SQLite. It does
not download a model, and it does not recommend a model.
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

QWEN = "qwen3.5:2b"
GEMMA = "gemma3:1b"
CLOUD_TAGS = frozenset({"gemma4:31b-cloud", "deepseek-v4.1-flash:cloud"})
RUNS: tuple[tuple[str, bool | None], ...] = (
    (QWEN, False),
    (GEMMA, None),
)
ENGINE_NAME = "ollama"
WARMUP_COUNT = 2
MEASURED_COUNT = 3
CONCURRENCY = 1
SAMPLE_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 120.0

DB_PATH = ROOT / "experiments" / "results" / "model-comparison.sqlite"
FINDINGS_PATH = ROOT / "docs" / "model-findings.md"


class QuantizationPairStop(Exception):
    """list_models showed a same-architecture pair with different quantization."""

    def __init__(self, left: ModelInfo, right: ModelInfo) -> None:
        self.left = left
        self.right = right
        super().__init__(
            "list_models shows two non-cloud models with the same architecture "
            "and different quantization levels"
        )


def main() -> int:
    """Run the eight profiles. Return 0 when the findings file is written."""
    config = OllamaConfig.from_env()
    if config.timeout_seconds != TIMEOUT_SECONDS:
        print("refusing to change the adapter timeout", file=sys.stderr)
        return 1
    try:
        asyncio.run(_run(config))
    except QuantizationPairStop as exc:
        print(
            "stopping before generate: "
            f"{exc.left.name} {exc.left.architecture} {exc.left.quantization}; "
            f"{exc.right.name} {exc.right.architecture} {exc.right.quantization}",
            file=sys.stderr,
        )
        return 1
    except OllamaError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


async def _run(config: OllamaConfig) -> None:
    adapter = OllamaAdapter(config)
    await adapter.show_model(QWEN)
    await adapter.show_model(GEMMA)
    listed = await adapter.list_models()
    pair = _quantization_pair(listed)
    if pair is not None:
        raise QuantizationPairStop(pair[0], pair[1])
    tags = {model.name: model for model in listed}
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
        for model, think in RUNS:
            for profile in PROFILES:
                print(f"running {model} {profile.name}", flush=True)
                shown = await adapter.show_model(model)
                version = await adapter.engine_version()
                fields = _metadata(shown, tags.get(model))
                snapshot = build_snapshot(
                    model=model,
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
                    think=think,
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
                    concurrency=CONCURRENCY,
                    profile_name=profile.name,
                    think=think,
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


def _quantization_pair(models: list[ModelInfo]) -> tuple[ModelInfo, ModelInfo] | None:
    """Return the first same-architecture pair with different quantization.

    Cloud tags stay out. A missing architecture does not count as a match.
    This check does not generate.
    """

    local = [model for model in models if model.name not in CLOUD_TAGS]
    for index, left in enumerate(local):
        for right in local[index + 1 :]:
            if left.architecture is None or right.architecture is None:
                continue
            if left.architecture != right.architecture:
                continue
            if left.quantization is None or right.quantization is None:
                continue
            if left.quantization != right.quantization:
                return left, right
    return None


def _metadata(shown: ModelInfo, tag: ModelInfo | None) -> ModelInfo:
    """Copy show fields, and fill a gap from the tags entry.

    The show payload omits size. Tags carry size. A field both omit stays
    unset. This does not invent a label.
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
        "# Model comparison findings",
        "",
        "These figures were loaded from `experiments/results/model-comparison.sqlite`.",
        "This file is a cross-model comparison.",
        "Experiment G was not run.",
        "Thinking on versus off was not run.",
        "It does not recommend a model.",
        "It does not attribute a difference to Q8 versus Q4.",
        "It does not call one configuration an improvement.",
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
    lines = [
        f"## {model} / {name}",
        "",
        f"- Model: {model}",
        f"- Profile name: {name}",
        f"- Think: {_think(snapshot.think)}",
        f"- Quantization: {_show(snapshot.quantization)}",
        f"- Parameter size: {_show(snapshot.parameter_size)}",
        f"- Size in bytes: {_show(snapshot.model_size_bytes)}",
        f"- Architecture: {_architecture(snapshot.architecture)}",
        f"- Engine version: {_show(snapshot.engine_version)}",
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


def _think(value: bool | None) -> str:
    """The stored flag is false or null."""
    if value is False:
        return "false"
    if value is None:
        return "null"
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
