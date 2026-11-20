"""One row per benchmark request.

Rows store the client clock and the raw provider fields. They do not store
percentiles, TTFT, or TPOT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Phase = Literal["warmup", "measured"]


@dataclass(frozen=True)
class RequestRecord:
    """One warm-up or measured call.

    ``end_to_end_ms`` is client end minus client start, in milliseconds.
    ``prompt_eval_duration`` and ``eval_duration`` are raw server nanoseconds.
    They are not copied into ``end_to_end_ms``. ``eval_count`` is the provider
    output-token count, not an HTTP chunk count.
    """

    phase: Phase
    model: str
    prompt: str
    num_predict: int | None
    client_start: float
    client_end: float
    end_to_end_ms: float
    success: bool
    error_type: str | None
    eval_count: int | None
    prompt_eval_count: int | None
    prompt_eval_duration: int | None
    eval_duration: int | None


@dataclass(frozen=True)
class BenchmarkRun:
    """Warm-up rows and measured rows, kept apart.

    Warm-up rows are stored on ``warmup`` and are not part of ``measured``.
    """

    warmup: tuple[RequestRecord, ...]
    measured: tuple[RequestRecord, ...]
