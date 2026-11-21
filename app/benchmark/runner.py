"""Benchmark runner.

Checks that the model is available, then calls streaming generate once per
warm-up and once per measured repetition. Warm-up is one call at a time.
The measured phase limits in-flight stream calls with a semaphore. The
default cap is 1. A cancel signal stops new measured launches, cancels
in-flight stream calls, and records each started attempt once. A failed
call is recorded and is not retried. An optional sampler records resource
samples after the model check. This module does not compute TTFT, TPOT,
throughput, or percentiles, and it does not open a database.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.benchmark.records import BenchmarkRun, Phase, RequestRecord
from app.core.exceptions import OllamaError
from app.inference.base import GenerateOptions, InferenceAdapter
from app.monitoring.sampler import ResourceSample


class BenchmarkRunner:
    """Warm-up one call at a time, then a capped measured phase.

    ``clock`` returns seconds, the same unit as ``time.perf_counter``. The
    default is that process clock. The same clock is passed into each
    stream call. ``concurrency`` limits measured stream calls only.
    ``cancel_event`` is an explicit signal the caller can set. ``sampler``
    is optional. With no sampler, the run records no samples.
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
        concurrency: int = 1,
        cancel_event: asyncio.Event | None = None,
        sampler: Callable[[], ResourceSample] | None = None,
        sample_interval: float = 1.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> BenchmarkRun:
        """Run warm-up, then the measured phase, and return both row groups.

        Defaults are 2 warm-up calls, 3 measured calls, and measured
        concurrency 1. ``show_model`` runs first. If the model is missing,
        that call raises and ``generate_stream`` is not used. Warm-up does
        not use the cap and does not overlap. A sampler starts only after
        ``show_model`` succeeds. The default sleep is ``asyncio.sleep``.
        """
        if warmup_count < 0:
            raise ValueError("warmup_count must be zero or greater")
        if measured_count < 0:
            raise ValueError("measured_count must be zero or greater")
        if concurrency < 1:
            raise ValueError("concurrency must be 1 or greater")
        if sampler is not None and sample_interval <= 0:
            raise ValueError("sample_interval must be greater than 0")

        await self._adapter.show_model(model)
        options = None if num_predict is None else GenerateOptions(num_predict=num_predict)
        samples: list[ResourceSample] = []
        sampling_errors: list[str] = []
        sample_task: asyncio.Task[None] | None = None
        if sampler is not None:
            sleep_fn = asyncio.sleep if sleep is None else sleep
            sample_task = asyncio.create_task(
                _sample_loop(sampler, sample_interval, sleep_fn, samples, sampling_errors)
            )
            await asyncio.sleep(0)
        try:
            warmup: list[RequestRecord] = []
            for _ in range(warmup_count):
                warmup.append(
                    await self._timed(
                        "warmup",
                        model,
                        prompt,
                        num_predict,
                        options,
                        record_cancellation=False,
                    )
                )
            measured = await self._measured_phase(
                model,
                prompt,
                num_predict,
                options,
                measured_count,
                concurrency,
                cancel_event,
            )
        finally:
            if sample_task is not None:
                sample_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await sample_task
        return BenchmarkRun(
            warmup=tuple(warmup),
            measured=measured,
            concurrency=concurrency,
            resource_samples=tuple(samples),
            sampling_error=sampling_errors[0] if sampling_errors else None,
        )

    async def _measured_phase(
        self,
        model: str,
        prompt: str,
        num_predict: int | None,
        options: GenerateOptions | None,
        measured_count: int,
        concurrency: int,
        cancel_event: asyncio.Event | None,
    ) -> tuple[RequestRecord, ...]:
        """Limit in-flight measured stream calls. Do not retry."""
        semaphore = asyncio.Semaphore(concurrency)
        tasks: list[asyncio.Task[RequestRecord | None]] = []

        def _release(_task: asyncio.Task[RequestRecord | None]) -> None:
            semaphore.release()

        watcher: asyncio.Task[None] | None = None
        if cancel_event is not None:
            watcher = asyncio.create_task(self._watch_cancel(cancel_event, tasks))
        try:
            for _ in range(measured_count):
                if cancel_event is not None and cancel_event.is_set():
                    break
                await semaphore.acquire()
                if cancel_event is not None and cancel_event.is_set():
                    semaphore.release()
                    break
                task = asyncio.create_task(
                    self._measured_call(model, prompt, num_predict, options, cancel_event)
                )
                task.add_done_callback(_release)
                tasks.append(task)
            finished = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            if watcher is not None:
                watcher.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await watcher

        rows: list[RequestRecord] = []
        for item in finished:
            if item is None or isinstance(item, asyncio.CancelledError):
                continue
            if isinstance(item, BaseException):
                raise item
            rows.append(item)
        return tuple(rows)

    async def _watch_cancel(
        self,
        cancel_event: asyncio.Event,
        tasks: list[asyncio.Task[RequestRecord | None]],
    ) -> None:
        """When the caller sets the signal, cancel measured stream calls in flight."""
        await cancel_event.wait()
        for task in tasks:
            task.cancel()

    async def _measured_call(
        self,
        model: str,
        prompt: str,
        num_predict: int | None,
        options: GenerateOptions | None,
        cancel_event: asyncio.Event | None,
    ) -> RequestRecord | None:
        """One measured slot. A call that has not started the stream is no row."""
        if cancel_event is not None and cancel_event.is_set():
            return None
        return await self._timed(
            "measured",
            model,
            prompt,
            num_predict,
            options,
            record_cancellation=True,
        )

    async def _timed(
        self,
        phase: Phase,
        model: str,
        prompt: str,
        num_predict: int | None,
        options: GenerateOptions | None,
        *,
        record_cancellation: bool,
    ) -> RequestRecord:
        """Time one stream call. End-to-end duration is client end minus start."""
        start = self._clock()
        try:
            result = await self._adapter.generate_stream(
                model,
                prompt,
                options,
                clock=self._clock,
            )
        except asyncio.CancelledError:
            if not record_cancellation:
                raise
            end = self._clock()
            return _record(
                phase,
                model,
                prompt,
                num_predict,
                start,
                end,
                success=False,
                error_type="CancelledError",
                metadata=None,
                first_content_at=None,
            )
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
                first_content_at=None,
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
            first_content_at=result.first_content_at,
        )


async def _sample_loop(
    sampler: Callable[[], ResourceSample],
    interval: float,
    sleep: Callable[[float], Awaitable[None]],
    samples: list[ResourceSample],
    sampling_errors: list[str],
) -> None:
    """Sample, sleep, and repeat until this task is cancelled.

    A sampler exception stops later samples and records the exception type
    name. It does not cancel inference calls. This loop does not call
    ``psutil``.
    """

    while True:
        try:
            sample = sampler()
        except Exception as exc:
            sampling_errors.append(type(exc).__name__)
            return
        samples.append(sample)
        try:
            await sleep(interval)
        except asyncio.CancelledError:
            return


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
    first_content_at: float | None,
) -> RequestRecord:
    return RequestRecord(
        phase=phase,
        model=model,
        prompt=prompt,
        num_predict=num_predict,
        client_start=start,
        first_content_at=first_content_at,
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
