"""Four live routing policies on one profile.

This file is not a pytest module. It runs static, workload-aware,
latency-constrained, and availability-aware on short_prompt_short_output.
Findings are written only from the rows loaded back out of SQLite. The
static experiment is the baseline. It does not download a model, it does
not send think true, and it does not recommend a policy.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import asyncio
import sqlite3
import time
from collections.abc import Sequence

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.benchmark.records import BenchmarkRun
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.workload import PROFILES
from app.core.config import OllamaConfig
from app.core.exceptions import OllamaError
from app.database.models import Base
from app.database.repository import StoredExperiment, load_experiments, save_experiment
from app.inference.base import ModelInfo
from app.inference.ollama import OllamaAdapter
from app.metrics.statistics import summarize
from app.monitoring.sampler import ResourceSample, psutil_probe, read_sample
from app.monitoring.snapshot import build_snapshot, psutil_hardware_probe
from app.optimization.comparison import Comparison, compare
from app.routing import (
    CatalogEntry,
    Decision,
    LatencyBudget,
    Measurement,
    RouteRequest,
    may_fallback,
    route,
)

GEMMA = "gemma3:1b"
QWEN = "qwen3.5:2b"
PROFILE_NAME = "short_prompt_short_output"
ENGINE_NAME = "ollama"
WARMUP_COUNT = 2
MEASURED_COUNT = 3
CONCURRENCY = 1
SAMPLE_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 120.0
POLICIES = (
    "static",
    "workload_aware",
    "latency_constrained",
    "availability_aware",
)
SUMMARY_FIELDS = (
    "average_ms",
    "median_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "error_rate",
    "generation_throughput_tps",
    "request_throughput_rps",
)

SOURCE_PATH = ROOT / "experiments" / "results" / "model-comparison.sqlite"
DB_PATH = ROOT / "experiments" / "results" / "routing-effectiveness.sqlite"
FINDINGS_PATH = ROOT / "docs" / "routing-findings.md"


class CatalogStop(Exception):
    """The stored catalog cannot be used. No findings file is written."""


def main() -> int:
    """Run the four policies. Return 0 when the findings file is written."""
    message = _timeout_message(OllamaConfig.from_env().timeout_seconds)
    if message is not None:
        print(message, file=sys.stderr)
        return 1
    try:
        asyncio.run(_run(OllamaConfig.from_env()))
    except CatalogStop as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OllamaError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


def _timeout_message(timeout_seconds: float) -> str | None:
    """Refuse a timeout other than the adapter default."""
    if timeout_seconds != TIMEOUT_SECONDS:
        return "refusing to change the adapter timeout"
    return None


async def _run(config: OllamaConfig) -> None:
    profile = next(item for item in PROFILES if item.name == PROFILE_NAME)
    adapter = OllamaAdapter(config)
    shown = {
        GEMMA: await adapter.show_model(GEMMA),
        QWEN: await adapter.show_model(QWEN),
    }
    source = _load_source()
    qwen_row = _require_profile(source, QWEN)
    gemma_row = _require_profile(source, GEMMA)
    catalog = _catalog(qwen_row, gemma_row)
    request = _request(_required_average(gemma_row))
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if FINDINGS_PATH.exists():
        FINDINGS_PATH.unlink()
    if DB_PATH.exists():
        DB_PATH.unlink()
    engine = create_engine("sqlite:///" + DB_PATH.resolve().as_posix())
    Base.metadata.create_all(engine)
    runner = BenchmarkRunner(adapter, clock=time.perf_counter)
    unavailable: set[str] = set()
    with Session(engine) as session:
        for policy in POLICIES:
            await _run_policy(
                session,
                runner,
                adapter,
                shown,
                profile.prompt,
                profile.num_predict,
                catalog,
                request,
                policy,
                unavailable,
            )
    with Session(engine) as session:
        loaded = load_experiments(session)
    text = _findings(loaded)
    FINDINGS_PATH.write_text(text, encoding="utf-8")
    with Session(engine) as session:
        reread = load_experiments(session)
    if _findings(reread) != text:
        raise RuntimeError("findings text does not match the stored experiments")


def _load_source() -> tuple[StoredExperiment, ...]:
    """Read the model-comparison file. This function does not write it."""
    if not SOURCE_PATH.is_file():
        raise CatalogStop("missing file: experiments/results/model-comparison.sqlite")

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(SOURCE_PATH)
        connection.execute("PRAGMA query_only = ON")
        return connection

    engine = create_engine("sqlite://", creator=connect)
    try:
        with Session(engine) as session:
            return load_experiments(session)
    finally:
        engine.dispose()


def _require_profile(rows: Sequence[StoredExperiment], model: str) -> StoredExperiment:
    """Return the one stored short-prompt row that has average and P95."""
    matched = [
        row
        for row in rows
        if row.snapshot.model == model and row.snapshot.profile_name == PROFILE_NAME
    ]
    if len(matched) == 0:
        raise CatalogStop(f"missing row: {model} {PROFILE_NAME}")
    if len(matched) != 1:
        raise CatalogStop(f"row is not unique: {model} {PROFILE_NAME}")
    summary = matched[0].summary
    if summary.average_ms is None or summary.p95_ms is None:
        raise CatalogStop(f"missing stored average or p95: {model} {PROFILE_NAME}")
    return matched[0]


def _required_average(row: StoredExperiment) -> float:
    average = row.summary.average_ms
    if average is None or row.summary.p95_ms is None:
        raise CatalogStop(f"missing stored average or p95: {row.snapshot.model} {PROFILE_NAME}")
    return average


def _catalog(qwen_row: StoredExperiment, gemma_row: StoredExperiment) -> tuple[CatalogEntry, ...]:
    """Catalog order is Qwen, then Gemma. Values are copied, not recomputed."""
    return (_entry(qwen_row), _entry(gemma_row))


def _entry(row: StoredExperiment) -> CatalogEntry:
    summary = row.summary
    return CatalogEntry(
        model=row.snapshot.model,
        measurements={
            PROFILE_NAME: Measurement(
                average_ms=summary.average_ms,
                median_ms=summary.median_ms,
                p50_ms=summary.p50_ms,
                p95_ms=summary.p95_ms,
                p99_ms=summary.p99_ms,
            )
        },
    )


def _request(gemma_average_ms: float) -> RouteRequest:
    """The budget maximum is Gemma's stored average. Required capabilities are empty."""
    return RouteRequest(
        profile_name=PROFILE_NAME,
        static_model=GEMMA,
        latency_budget=LatencyBudget("average_ms", gemma_average_ms),
    )


async def _run_policy(
    session: Session,
    runner: BenchmarkRunner,
    adapter: OllamaAdapter,
    shown: dict[str, ModelInfo],
    prompt: str,
    num_predict: int,
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
    policy: str,
    unavailable: set[str],
) -> None:
    """Run one policy. Only availability-aware may start one replacement model."""
    if policy != "availability_aware":
        decision = route(policy, catalog, request)
        if decision.selected_model is None:
            raise CatalogStop(f"{policy} selected no model")
        await _store_decision(session, runner, adapter, shown, prompt, num_predict, decision)
        return
    decision = route(policy, catalog, request, unavailable)
    for attempt in (1, 2):
        model = decision.selected_model
        if model is None:
            if attempt == 1:
                raise CatalogStop("availability_aware selected no model")
            return
        if model in unavailable:
            return
        try:
            run = await _store_decision(
                session,
                runner,
                adapter,
                shown,
                prompt,
                num_predict,
                decision,
            )
        except OllamaError:
            unavailable.add(model)
            if attempt == 2:
                return
            decision = route(policy, catalog, request, unavailable)
            continue
        if attempt == 2 or not may_fallback(run.measured):
            return
        unavailable.add(model)
        decision = route(policy, catalog, request, unavailable)


async def _store_decision(
    session: Session,
    runner: BenchmarkRunner,
    adapter: OllamaAdapter,
    shown: dict[str, ModelInfo],
    prompt: str,
    num_predict: int,
    decision: Decision,
) -> BenchmarkRun:
    """Run the selected model once and store that experiment.

    ``runner.run`` calls ``show_model`` before any row. An ``OllamaError``
    from that call leaves this function before ``save_experiment``.
    """
    model = decision.selected_model
    if model is None:
        raise CatalogStop(f"{decision.policy} selected no model")
    think = False if model == QWEN else None
    info = shown[model]
    print(
        f"running {decision.policy} selected {model} "
        f"fallback_count {decision.fallback_count}",
        flush=True,
    )
    version = await adapter.engine_version()
    snapshot = build_snapshot(
        model=model,
        prompt=prompt,
        num_predict=num_predict,
        warmup_count=WARMUP_COUNT,
        measured_count=MEASURED_COUNT,
        concurrency=CONCURRENCY,
        engine_name=ENGINE_NAME,
        engine_version=version,
        clock=time.perf_counter,
        probe=psutil_hardware_probe,
        profile_name=PROFILE_NAME,
        think=think,
        quantization=info.quantization,
        parameter_size=info.parameter_size,
        model_size_bytes=info.size,
        architecture=info.architecture,
        routing_policy=decision.policy,
        preferred_model=decision.preferred_model,
        fallback_count=decision.fallback_count,
        retry_count=0,
    )
    run = await runner.run(
        model,
        prompt,
        num_predict=num_predict,
        warmup_count=WARMUP_COUNT,
        measured_count=MEASURED_COUNT,
        concurrency=CONCURRENCY,
        profile_name=PROFILE_NAME,
        think=think,
        sampler=_sample,
        sample_interval=SAMPLE_INTERVAL_SECONDS,
    )
    summary = summarize(run)
    save_experiment(session, run, snapshot, summary)
    session.commit()
    return run


def _sample() -> ResourceSample:
    """One real sample. The first CPU reading may be 0. That 0 is kept."""
    return read_sample(psutil_probe, time.perf_counter)


def _comparison_pairs(
    experiments: Sequence[StoredExperiment],
) -> tuple[tuple[StoredExperiment, StoredExperiment], ...]:
    """Static is the baseline. Availability uses the fallback row when one was stored."""
    baseline = _one(
        [row for row in experiments if row.snapshot.routing_policy == "static"],
        "static",
    )
    pairs: list[tuple[StoredExperiment, StoredExperiment]] = []
    for policy in POLICIES:
        if policy == "static":
            continue
        pairs.append((baseline, _candidate(experiments, policy)))
    return tuple(pairs)


def _candidate(experiments: Sequence[StoredExperiment], policy: str) -> StoredExperiment:
    rows = [row for row in experiments if row.snapshot.routing_policy == policy]
    if policy == "availability_aware":
        fallbacks = [row for row in rows if row.snapshot.fallback_count == 1]
        if fallbacks:
            return _one(fallbacks, "availability_aware fallback")
    return _one(rows, policy)


def _one(rows: Sequence[StoredExperiment], label: str) -> StoredExperiment:
    if len(rows) == 0:
        raise CatalogStop(f"missing stored experiment: {label}")
    if len(rows) != 1:
        raise CatalogStop(f"stored experiment is not unique: {label}")
    return rows[0]


def _findings(experiments: Sequence[StoredExperiment]) -> str:
    """Render the note from loaded experiments. Unset fields stay unset."""
    pairs = _comparison_pairs(experiments)
    fell_back = any(row.snapshot.fallback_count == 1 for row in experiments)
    lines = [
        "# Routing effectiveness findings",
        "",
        "These figures were loaded from `experiments/results/routing-effectiveness.sqlite`.",
        "This file describes the stored summaries.",
        "The static experiment is the baseline for each comparison.",
        "A delta is the candidate's stored aggregate minus the baseline's stored aggregate.",
        "The request timeout was the adapter default of 120 seconds.",
        "The measured count is 3.",
        "The retry count is 0.",
        "Gemma's request does not send think.",
        "Qwen was run with think false when Qwen was selected.",
        "Thinking was not turned on.",
        "A pair whose models differ is a cross-model comparison.",
        "This file does not name a winner.",
        "This file does not recommend a policy.",
        "It does not call a policy an improvement.",
        "",
    ]
    if not fell_back:
        lines.append("The fallback count is 0.")
        lines.append("")
    for stored in experiments:
        lines.extend(_run_lines(stored))
    for baseline, candidate in pairs:
        lines.extend(_pair_lines(baseline, candidate, compare(baseline, candidate)))
    return "\n".join(lines) + "\n"


def _run_lines(stored: StoredExperiment) -> list[str]:
    snapshot = stored.snapshot
    summary = stored.summary
    error_values = [
        f"{row.phase} {row.error_type}"
        for row in (*stored.warmup, *stored.measured)
        if row.error_type is not None
    ]
    lines = [
        f"## {_show(snapshot.routing_policy)} / {_show(snapshot.model)} / experiment {stored.experiment_id}",
        "",
        f"- Routing policy: {_show(snapshot.routing_policy)}",
        f"- Selected model: {_show(snapshot.model)}",
        f"- Preferred model: {_show(snapshot.preferred_model)}",
        f"- Fallback count: {_show(snapshot.fallback_count)}",
        f"- Retry count: {_show(snapshot.retry_count)}",
        f"- Think: {_think(snapshot.think)}",
        f"- Measured count: {_show(snapshot.measured_count)}",
        f"- Error rate: {_show(summary.error_rate)}",
        f"- Average: {_show(summary.average_ms)}",
        f"- Median: {_show(summary.median_ms)}",
        f"- P50: {_show(summary.p50_ms)}",
        f"- P95: {_show(summary.p95_ms)}",
        f"- P99: {_show(summary.p99_ms)}",
        f"- Generation throughput: {_show(summary.generation_throughput_tps)}",
        f"- Request throughput: {_show(summary.request_throughput_rps)}",
        "- Stored error_type values: " + (", ".join(error_values) if error_values else "none"),
        "",
    ]
    return lines


def _pair_lines(
    baseline: StoredExperiment,
    candidate: StoredExperiment,
    result: Comparison,
) -> list[str]:
    lines = [
        f"## Comparison against static / {_show(candidate.snapshot.routing_policy)}",
        "",
        f"- Baseline experiment id: {baseline.experiment_id}",
        f"- Candidate experiment id: {candidate.experiment_id}",
        f"- Baseline model: {_show(baseline.snapshot.model)}",
        f"- Candidate model: {_show(candidate.snapshot.model)}",
        f"- Candidate preferred model: {_show(candidate.snapshot.preferred_model)}",
        f"- Candidate fallback count: {_show(candidate.snapshot.fallback_count)}",
    ]
    if candidate.snapshot.fallback_count == 1:
        lines.append("- The candidate is the fallback experiment.")
    if baseline.snapshot.model != candidate.snapshot.model:
        lines.append("- This pair is a cross-model comparison.")
    for name in SUMMARY_FIELDS:
        lines.append(f"- Baseline {name}: {_show(getattr(baseline.summary, name))}")
        lines.append(f"- Candidate {name}: {_show(getattr(candidate.summary, name))}")
        lines.append(f"- {name} delta: {_show(getattr(result, name + '_delta'))}")
    if result.sign_sentence is not None:
        lines.append(f"- Sign sentence: {result.sign_sentence}")
    lines.append("")
    return lines


def _think(value: bool | None) -> str:
    """The stored flag. An omitted flag stays unset."""
    if value is None:
        return "unset"
    if value is False:
        return "false"
    return "true"


def _show(value: object) -> str:
    """Format one stored field. None stays unset."""
    if value is None:
        return "unset"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
