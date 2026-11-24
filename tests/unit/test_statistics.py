"""Aggregate statistics from constructed rows.

Ollama is not contacted. Clock values and durations are fixtures.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

from app.benchmark.records import BenchmarkRun, RequestRecord
from app.benchmark.runner import BenchmarkRunner
from app.inference.base import InferenceAdapter
from app.inference.ollama import OllamaAdapter
from app.metrics.statistics import (
    AggregateSummary,
    average_ms,
    error_rate,
    median_ms,
    percentile_ms,
    summarize,
)


def _row(**overrides: object) -> RequestRecord:
    fields: dict[str, object] = {
        "phase": "measured",
        "model": "gemma3:1b",
        "prompt": "Hi",
        "num_predict": None,
        "client_start": 0.0,
        "first_content_at": 0.0,
        "client_end": 2.0,
        "end_to_end_ms": 2000.0,
        "success": True,
        "error_type": None,
        "eval_count": 10,
        "prompt_eval_count": None,
        "prompt_eval_duration": None,
        "eval_duration": 20,
    }
    fields.update(overrides)
    return RequestRecord(**fields)


def test_five_value_sample_returns_average_median_and_percentiles() -> None:
    measured = tuple(_row(end_to_end_ms=value) for value in (100, 110, 120, 130, 2000))
    warmup = _row(phase="warmup", end_to_end_ms=9000)
    run = BenchmarkRun(warmup=(warmup,), measured=measured)

    assert average_ms(run) == 492
    assert median_ms(run) == 120
    assert percentile_ms(run, 50) == 120
    assert percentile_ms(run, 95) == 2000
    assert percentile_ms(run, 99) == 2000

    summary = summarize(run)
    assert summary.average_ms == 492
    assert summary.median_ms == 120
    assert summary.p50_ms == 120
    assert summary.p95_ms == 2000
    assert summary.p99_ms == 2000
    assert summary.error_rate == 0


def test_even_count_median_differs_from_nearest_rank_p50() -> None:
    measured = tuple(_row(end_to_end_ms=value) for value in (100, 110, 130, 2000))
    run = BenchmarkRun(warmup=(), measured=measured)

    assert median_ms(run) == 120
    assert percentile_ms(run, 50) == 110

    summary = summarize(run)
    assert summary.median_ms == 120
    assert summary.p50_ms == 110


def test_failed_row_with_stamp_stays_out_of_the_latency_sample() -> None:
    run = BenchmarkRun(
        warmup=(),
        measured=(
            _row(end_to_end_ms=100),
            _row(end_to_end_ms=110),
            _row(end_to_end_ms=120),
            _row(
                success=False,
                error_type="OllamaTimeoutError",
                first_content_at=0.8,
                end_to_end_ms=50,
                eval_count=1000,
            ),
        ),
    )

    assert average_ms(run) == 110
    assert median_ms(run) == 110
    assert percentile_ms(run, 50) == 110


def test_three_successes_and_one_failure_return_error_rate_0_25() -> None:
    run = BenchmarkRun(
        warmup=(),
        measured=(
            _row(end_to_end_ms=100),
            _row(end_to_end_ms=110),
            _row(end_to_end_ms=120),
            _row(
                success=False,
                error_type="OllamaTimeoutError",
                first_content_at=0.4,
                end_to_end_ms=5000,
            ),
        ),
    )

    assert error_rate(run) == 0.25


def test_cancelled_row_returns_error_rate_0() -> None:
    run = BenchmarkRun(
        warmup=(),
        measured=(
            _row(end_to_end_ms=100),
            _row(
                success=False,
                error_type="CancelledError",
                first_content_at=None,
                end_to_end_ms=500,
            ),
        ),
    )

    assert error_rate(run) == 0
    assert average_ms(run) == 100


def test_only_adapter_failures_leave_the_five_latency_fields_unset() -> None:
    run = BenchmarkRun(
        warmup=(),
        measured=(
            _row(success=False, error_type="OllamaTimeoutError", end_to_end_ms=100),
            _row(success=False, error_type="MalformedResponseError", end_to_end_ms=200),
        ),
    )

    assert average_ms(run) is None
    assert median_ms(run) is None
    assert percentile_ms(run, 50) is None
    assert percentile_ms(run, 95) is None
    assert percentile_ms(run, 99) is None


def test_empty_measured_set_leaves_error_rate_unset() -> None:
    run = BenchmarkRun(
        warmup=(_row(phase="warmup", end_to_end_ms=9000),),
        measured=(),
    )

    assert error_rate(run) is None
    assert average_ms(run) is None
    assert median_ms(run) is None
    assert percentile_ms(run, 50) is None
    assert percentile_ms(run, 95) is None
    assert percentile_ms(run, 99) is None


def test_only_cancellations_leave_error_rate_unset() -> None:
    run = BenchmarkRun(
        warmup=(),
        measured=(
            _row(success=False, error_type="CancelledError", end_to_end_ms=100),
            _row(success=False, error_type="CancelledError", end_to_end_ms=200),
        ),
    )

    assert error_rate(run) is None
    assert average_ms(run) is None


def test_summarize_fills_fields_from_the_same_rules() -> None:
    run = BenchmarkRun(
        warmup=(
            _row(
                phase="warmup",
                client_start=-5.0,
                client_end=-1.0,
                first_content_at=-3.0,
                end_to_end_ms=9000,
                eval_count=1000,
            ),
        ),
        measured=(
            _row(
                client_start=0.0,
                first_content_at=2.0,
                client_end=4.0,
                end_to_end_ms=100,
                eval_count=10,
            ),
            _row(
                client_start=1.0,
                first_content_at=3.0,
                client_end=5.0,
                end_to_end_ms=300,
                eval_count=20,
            ),
            _row(
                success=False,
                error_type="OllamaTimeoutError",
                client_start=0.0,
                first_content_at=0.5,
                client_end=10.0,
                end_to_end_ms=10000,
                eval_count=1000,
                eval_duration=10**18,
            ),
        ),
    )

    summary = summarize(run)

    assert isinstance(summary, AggregateSummary)
    assert summary.average_ms == 200
    assert summary.median_ms == 200
    assert summary.p50_ms == 100
    assert summary.p95_ms == 300
    assert summary.p99_ms == 300
    assert summary.error_rate == 1 / 3
    assert summary.generation_throughput_tps == 7.5
    assert summary.request_throughput_rps == 0.2


def test_runner_and_adapter_expose_no_percentile_or_throughput_helper() -> None:
    import app.benchmark.runner as runner_module
    import app.inference.base as base_module
    import app.inference.ollama as ollama_module

    banned = ("percentile", "ttft", "tpot", "throughput")
    names = [name.lower() for name in dir(BenchmarkRunner)]
    names.extend(name.lower() for name in dir(OllamaAdapter))
    names.extend(name.lower() for name in dir(InferenceAdapter))
    for module in (runner_module, ollama_module, base_module):
        names.extend(name.lower() for name in dir(module))
    for name in names:
        for word in banned:
            assert word not in name
