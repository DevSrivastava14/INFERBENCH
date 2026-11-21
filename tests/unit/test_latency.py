"""Request-level latency from one constructed row.

The clocks are the Day 1 teaching fixtures. Ollama is not contacted.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

from app.benchmark.records import RequestRecord
from app.metrics.latency import decode_duration_ms, tpot_ms, ttft_ms


def _row(**overrides: object) -> RequestRecord:
    fields: dict[str, object] = {
        "phase": "measured",
        "model": "gemma3:1b",
        "prompt": "Hi",
        "num_predict": None,
        "client_start": 0.0,
        "first_content_at": 0.8,
        "client_end": 3.0,
        "end_to_end_ms": 3000.0,
        "success": True,
        "error_type": None,
        "eval_count": 21,
        "prompt_eval_count": None,
        "prompt_eval_duration": 10,
        "eval_duration": 20,
    }
    fields.update(overrides)
    return RequestRecord(**fields)


def test_teaching_clocks_return_ttft_decode_and_tpot() -> None:
    row = _row()

    assert ttft_ms(row) == 800
    assert decode_duration_ms(row) == 2200
    assert tpot_ms(row) == 110


def test_eval_count_below_two_leaves_tpot_unset() -> None:
    row = _row(eval_count=1)

    assert ttft_ms(row) == 800
    assert decode_duration_ms(row) == 2200
    assert tpot_ms(row) is None


def test_failed_row_leaves_ttft_decode_and_tpot_unset() -> None:
    row = _row(success=False, error_type="OllamaTimeoutError")

    assert ttft_ms(row) is None
    assert decode_duration_ms(row) is None
    assert tpot_ms(row) is None
