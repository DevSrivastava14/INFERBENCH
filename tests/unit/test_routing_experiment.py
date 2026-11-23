"""Checks in the routing-experiment script. No live server.

The script module is loaded here. Pytest does not collect that script.
This file does not read ``docs/routing-findings.md`` or
``experiments/results/model-comparison.sqlite``. Clock values and aggregate
numbers below are fixtures. No test asserts a latency number from a live server.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.benchmark.records import RequestRecord
from app.database.repository import StoredExperiment
from app.metrics.statistics import AggregateSummary
from app.monitoring.snapshot import ConfigurationSnapshot

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_routing_experiment.py"
_SPEC = importlib.util.spec_from_file_location("run_routing_experiment", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_timeout_other_than_120_is_refused() -> None:
    assert _MODULE._timeout_message(120.0) is None
    assert _MODULE._timeout_message(30.0) == "refusing to change the adapter timeout"


def test_a_missing_or_duplicate_profile_row_is_rejected() -> None:
    present = _stored(1, policy="static", model="gemma3:1b", average=40.0, p95=70.0)
    missing_p95 = _stored(2, policy="static", model="qwen3.5:2b", average=50.0, p95=None)

    with pytest.raises(_MODULE.CatalogStop):
        _MODULE._require_profile((), "gemma3:1b")
    with pytest.raises(_MODULE.CatalogStop):
        _MODULE._require_profile((present, present), "gemma3:1b")
    with pytest.raises(_MODULE.CatalogStop):
        _MODULE._require_profile((missing_p95,), "qwen3.5:2b")


def test_catalog_order_is_qwen_then_gemma_and_the_budget_is_the_stored_average() -> None:
    qwen = _stored(1, policy="static", model="qwen3.5:2b", average=50.0, p95=80.0)
    gemma = _stored(2, policy="static", model="gemma3:1b", average=40.0, p95=70.0)

    catalog = _MODULE._catalog(qwen, gemma)
    request = _MODULE._request(40.0)

    assert [entry.model for entry in catalog] == ["qwen3.5:2b", "gemma3:1b"]
    assert catalog[0].measurements["short_prompt_short_output"].p95_ms == 80.0
    assert catalog[1].measurements["short_prompt_short_output"].average_ms == 40.0
    assert request.static_model == "gemma3:1b"
    assert request.profile_name == "short_prompt_short_output"
    assert request.required_capabilities == frozenset()
    assert request.max_model_size_bytes is None
    assert request.latency_budget is not None
    assert request.latency_budget.metric == "average_ms"
    assert request.latency_budget.maximum == 40.0


def test_static_is_the_baseline_when_fallback_count_is_0() -> None:
    static = _stored(1, policy="static", model="gemma3:1b", average=100.0, p95=110.0)
    workload = _stored(2, policy="workload_aware", model="gemma3:1b", average=140.0, p95=150.0)
    limited = _stored(
        3,
        policy="latency_constrained",
        model="gemma3:1b",
        average=140.0,
        p95=150.0,
    )
    aware = _stored(
        4,
        policy="availability_aware",
        model="gemma3:1b",
        average=140.0,
        p95=150.0,
        fallback_count=0,
        preferred="gemma3:1b",
    )
    experiments = (static, workload, limited, aware)

    pairs = _MODULE._comparison_pairs(experiments)
    text = _MODULE._findings(experiments)

    assert [baseline.experiment_id for baseline, _candidate in pairs] == [1, 1, 1]
    assert [candidate.experiment_id for _baseline, candidate in pairs] == [2, 3, 4]
    assert "The static experiment is the baseline for each comparison." in text
    assert "The fallback count is 0." in text
    assert "The candidate is the fallback experiment." not in text
    assert "This pair is a cross-model comparison." not in text
    assert "average_ms delta: 40" in text
    assert "The request timeout was the adapter default of 120 seconds." in text
    assert "The measured count is 3." in text
    assert "The retry count is 0." in text
    assert "Gemma's request does not send think." in text
    assert "Qwen was run with think false when Qwen was selected." in text
    assert "Thinking was not turned on." in text
    assert "A pair whose models differ is a cross-model comparison." in text
    assert "This file does not name a winner." in text
    assert "This file does not recommend a policy." in text
    assert "It does not call a policy an improvement." in text


def test_fallback_experiment_is_the_availability_candidate() -> None:
    static = _stored(1, policy="static", model="gemma3:1b", average=100.0, p95=110.0)
    workload = _stored(2, policy="workload_aware", model="qwen3.5:2b", average=80.0, p95=90.0)
    limited = _stored(
        3,
        policy="latency_constrained",
        model="gemma3:1b",
        average=100.0,
        p95=110.0,
    )
    failed = _stored(
        4,
        policy="availability_aware",
        model="qwen3.5:2b",
        average=None,
        p95=None,
        fallback_count=0,
        preferred="qwen3.5:2b",
        error_rate=1.0,
    )
    fallback = _stored(
        5,
        policy="availability_aware",
        model="gemma3:1b",
        average=100.0,
        p95=110.0,
        fallback_count=1,
        preferred="qwen3.5:2b",
    )
    experiments = (static, workload, limited, failed, fallback)

    pairs = _MODULE._comparison_pairs(experiments)
    text = _MODULE._findings(experiments)

    assert [candidate.experiment_id for _baseline, candidate in pairs] == [2, 3, 5]
    assert pairs[2][0].experiment_id == 1
    assert "The candidate is the fallback experiment." in text
    assert "The fallback count is 0." not in text
    assert "This pair is a cross-model comparison." in text
    assert "- Candidate experiment id: 5" in text
    assert "- Selected model: qwen3.5:2b" in text
    assert "- Fallback count: 1" in text


def _stored(
    experiment_id: int,
    *,
    policy: str,
    model: str,
    average: float | None,
    p95: float | None,
    fallback_count: int = 0,
    preferred: str | None = None,
    error_rate: float = 0.0,
) -> StoredExperiment:
    row = RequestRecord(
        phase="measured",
        model=model,
        prompt="fixture",
        num_predict=32,
        client_start=1.0,
        first_content_at=1.5,
        client_end=2.0,
        end_to_end_ms=1000.0,
        success=error_rate == 0.0,
        error_type=None if error_rate == 0.0 else "OllamaTimeoutError",
        eval_count=3,
        prompt_eval_count=4,
        prompt_eval_duration=None,
        eval_duration=None,
    )
    snapshot = ConfigurationSnapshot(
        model=model,
        prompt="fixture",
        num_predict=32,
        warmup_count=2,
        measured_count=3,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.fixture",
        capture_time=1.0,
        cpu_model="fixture-cpu",
        logical_cpu_count=2,
        total_ram_bytes=8,
        python_version="3.x",
        profile_name="short_prompt_short_output",
        think=False if model == "qwen3.5:2b" else None,
        routing_policy=policy,
        preferred_model=preferred if preferred is not None else model,
        fallback_count=fallback_count,
        retry_count=0,
    )
    return StoredExperiment(
        experiment_id=experiment_id,
        snapshot=snapshot,
        warmup=(),
        measured=(row,),
        resource_samples=(),
        sampling_error=None,
        summary=AggregateSummary(
            average_ms=average,
            median_ms=average,
            p50_ms=p95,
            p95_ms=p95,
            p99_ms=p95,
            error_rate=error_rate,
            generation_throughput_tps=None,
            request_throughput_rps=None,
        ),
    )
