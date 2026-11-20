"""Sequential benchmark runner.

Checks that the model is available, then calls non-streaming generate once
per warm-up and once per measured repetition. Each call is timed around the
await with the benchmark process clock. A failed call is recorded and is not
retried. This module does not compute TTFT, TPOT, throughput, or percentiles.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.benchmark.records import BenchmarkRun, Phase, RequestRecord
from app.core.exceptions import OllamaError
from app.inference.base import GenerateOptions, InferenceAdapter


class BenchmarkRunner:
    """Warm-up, then measured repetitions, one call at a time.

    ``clock`` returns seconds, the same unit as ``time.perf_counter``. The
    default is that process clock.
    """

    def __init__(
        self,
        adapter: InferenceAdapter,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._adapter = adapter
        self._clock = clock if clock is not None else time.perf_counter

    async def run(
        self,
        model: str,
        prompt: str,
        *,
        num_predict: int | None = None,
        warmup_count: int = 2,
        measured_count: int = 3,
    ) -> BenchmarkRun:
        """Run the sequential procedure and return the two row groups.

        Defaults are 2 warm-up calls and 3 measured calls. ``show_model`` runs
        first. If the model is missing, that call raises and ``generate`` is
        not used.
        """
        if warmup_count < 0:
            raise ValueError("warmup_count must be zero or greater")
        if measured_count < 0:
            raise ValueError("measured_count must be zero or greater")

        await self._adapter.show_model(model)
        options = None if num_predict is None else GenerateOptions(num_predict=num_predict)
        warmup: list[RequestRecord] = []
        for _ in range(warmup_count):
            warmup.append(await self._one("warmup", model, prompt, num_predict, options))
        measured: list[RequestRecord] = []
        for _ in range(measured_count):
            measured.append(await self._one("measured", model, prompt, num_predict, options))
        return BenchmarkRun(warmup=tuple(warmup), measured=tuple(measured))

    async def _one(
        self,
        phase: Phase,
        model: str,
        prompt: str,
        num_predict: int | None,
        options: GenerateOptions | None,
    ) -> RequestRecord:
        start = self._clock()
        try:
            result = await self._adapter.generate(model, prompt, options)
        except OllamaError as exc:
            end = self._clock()
            return _record(
                phase,
                model,
                prompt,
                num_predict,
                start,
                end,
                success=False,
                error_type=type(exc).__name__,
                metadata=None,
            )
        end = self._clock()
        return _record(
            phase,
            model,
            prompt,
            num_predict,
            start,
            end,
            success=True,
            error_type=None,
            metadata=result.metadata,
        )


def _record(
    phase: Phase,
    model: str,
    prompt: str,
    num_predict: int | None,
    start: float,
    end: float,
    *,
    success: bool,
    error_type: str | None,
    metadata: dict[str, Any] | None,
) -> RequestRecord:
    return RequestRecord(
        phase=phase,
        model=model,
        prompt=prompt,
        num_predict=num_predict,
        client_start=start,
        client_end=end,
        end_to_end_ms=(end - start) * 1000.0,
        success=success,
        error_type=error_type,
        eval_count=_raw_int(metadata, "eval_count"),
        prompt_eval_count=_raw_int(metadata, "prompt_eval_count"),
        prompt_eval_duration=_raw_int(metadata, "prompt_eval_duration"),
        eval_duration=_raw_int(metadata, "eval_duration"),
    )


def _raw_int(metadata: dict[str, Any] | None, key: str) -> int | None:
    if metadata is None:
        return None
    value = metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
