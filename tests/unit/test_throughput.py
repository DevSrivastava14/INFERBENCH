"""Throughput from constructed rows.

Ollama is not contacted. Clock values and durations are fixtures.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

from app.benchmark.records import BenchmarkRun, RequestRecord
from app.metrics.throughput import generation_throughput_tps, request_throughput_rps


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


def _run(
    *measured: RequestRecord,
    warmup: tuple[RequestRecord, ...] = (),
) -> BenchmarkRun:
    return BenchmarkRun(warmup=warmup, measured=measured)


def test_ten_and_twenty_tokens_return_7_5() -> None:
    run = _run(
        _row(eval_count=10, first_content_at=0.0, client_end=2.0),
        _row(eval_count=20, first_content_at=0.0, client_end=2.0),
    )

    assert generation_throughput_tps(run) == 7.5


def test_one_token_returns_half() -> None:
    run = _run(_row(eval_count=1, first_content_at=0.0, client_end=2.0))

    assert generation_throughput_tps(run) == 0.5


def test_missing_eval_count_drops_row_from_both_sums() -> None:
    run = _run(
        _row(eval_count=10, first_content_at=0.0, client_end=2.0),
        _row(eval_count=None, first_content_at=0.0, client_end=2.0),
    )

    assert generation_throughput_tps(run) == 5


def test_huge_eval_duration_does_not_change_generation_throughput() -> None:
    ordinary = _run(
        _row(eval_count=10, eval_duration=20),
        _row(eval_count=20, eval_duration=20),
    )
    huge = _run(
        _row(eval_count=10, eval_duration=10**18),
        _row(eval_count=20, eval_duration=10**18),
    )

    assert generation_throughput_tps(ordinary) == 7.5
    assert generation_throughput_tps(huge) == 7.5


def test_failed_row_with_stamp_stays_out_of_generation_throughput() -> None:
    run = _run(
        _row(eval_count=10, first_content_at=0.0, client_end=2.0),
        _row(
            success=False,
            error_type="OllamaTimeoutError",
            first_content_at=0.4,
            client_start=0.0,
            client_end=2.0,
            eval_count=1000,
            eval_duration=10**18,
        ),
    )

    assert generation_throughput_tps(run) == 5


def test_overlapping_spans_return_0_4_and_warmup_does_not_widen_window() -> None:
    run = _run(
        _row(client_start=0.0, client_end=4.0),
        _row(client_start=1.0, client_end=5.0),
        warmup=(_row(phase="warmup", client_start=-5.0, client_end=-1.0),),
    )

    assert request_throughput_rps(run) == 0.4


def test_failed_span_beside_success_returns_0_1() -> None:
    run = _run(
        _row(client_start=1.0, client_end=5.0),
        _row(
            success=False,
            error_type="OllamaTimeoutError",
            client_start=0.0,
            client_end=10.0,
            first_content_at=1.0,
        ),
    )

    assert request_throughput_rps(run) == 0.1


def test_zero_window_leaves_request_throughput_unset() -> None:
    run = _run(_row(client_start=1.0, client_end=1.0, first_content_at=1.0))

    assert request_throughput_rps(run) is None


def test_zero_completed_requests_over_a_positive_window_returns_0() -> None:
    run = _run(
        _row(
            success=False,
            error_type="OllamaTimeoutError",
            client_start=0.0,
            client_end=10.0,
            first_content_at=1.0,
        )
    )

    assert request_throughput_rps(run) == 0


def test_cancelled_row_sets_the_request_throughput_window() -> None:
    run = _run(
        _row(client_start=1.0, client_end=5.0),
        _row(
            success=False,
            error_type="CancelledError",
            client_start=0.0,
            client_end=10.0,
            first_content_at=None,
        ),
    )

    assert request_throughput_rps(run) == 0.1


def test_generation_throughput_stays_unset_when_no_measured_row_qualifies() -> None:
    run = _run(
        _row(
            success=False,
            error_type="OllamaTimeoutError",
            first_content_at=0.4,
            eval_count=10,
        )
    )

    assert generation_throughput_tps(run) is None


def test_empty_measured_set_leaves_request_throughput_unset() -> None:
    run = BenchmarkRun(
        warmup=(_row(phase="warmup", client_start=-5.0, client_end=-1.0),),
        measured=(),
    )

    assert request_throughput_rps(run) is None
