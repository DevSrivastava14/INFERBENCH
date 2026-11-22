"""One row per benchmark request.

Rows store the client clock, the first-content stamp, and the raw provider
fields. They do not store percentiles, TTFT, or TPOT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.monitoring.sampler import ResourceSample

Phase = Literal["warmup", "measured"]


@dataclass(frozen=True)
class RequestRecord:
    """One warm-up or measured call.

    ``end_to_end_ms`` is client end minus client start, in milliseconds.
    ``first_content_at`` is the runner's clock at the first non-empty
    ``response``. It is unset on a failed or cancelled row. It is not TTFT.
    ``prompt_eval_duration`` and ``eval_duration`` are raw server nanoseconds.
    They are not copied into ``end_to_end_ms``. ``eval_count`` is the provider
    output-token count, not an HTTP chunk count. ``chunk_count`` is not a field.
    """

    phase: Phase
    model: str
    prompt: str
    num_predict: int | None
    client_start: float
    first_content_at: float | None
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
    ``concurrency`` is the measured-phase cap the caller requested. Warm-up
    does not use that cap. ``resource_samples`` is empty when the run had no
    sampler. ``sampling_error`` is the exception type name when the sampler
    stopped, and is unset otherwise. ``profile_name`` is the name the caller
    passed. It is unset when the caller omits it. This object does not look
    up a profile catalog.
    """

    warmup: tuple[RequestRecord, ...]
    measured: tuple[RequestRecord, ...]
    concurrency: int = 1
    resource_samples: tuple[ResourceSample, ...] = ()
    sampling_error: str | None = None
    profile_name: str | None = None
