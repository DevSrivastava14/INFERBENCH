"""Benchmark tests. The adapter is a fake.

Ollama is not contacted. Clock values and duration integers are fixtures.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from app.benchmark.runner import BenchmarkRunner
from app.core.exceptions import ModelNotInstalledError, OllamaTimeoutError
from app.inference.base import (
    GenerateOptions,
    GenerateResult,
    InferenceAdapter,
    ModelInfo,
    StreamGenerateResult,
)
from app.inference.ollama import OllamaAdapter

CLOCK_START = 100.0
CLOCK_STEP = 0.25
FIXTURE_EVAL_COUNT = 2
FIXTURE_CHUNK_COUNT = 9
FIXTURE_EVAL_DURATION = 20
FIXTURE_PROMPT_EVAL_DURATION = 10

METADATA = {
    "response": "ok",
    "eval_count": FIXTURE_EVAL_COUNT,
    "prompt_eval_count": 5,
    "prompt_eval_duration": FIXTURE_PROMPT_EVAL_DURATION,
    "eval_duration": FIXTURE_EVAL_DURATION,
    "chunk_count": FIXTURE_CHUNK_COUNT,
}


class FakeClock:
    """Returns seconds, then moves forward by a fixed step."""

    def __init__(self) -> None:
        self._now = CLOCK_START

    def __call__(self) -> float:
        current = self._now
        self._now += CLOCK_STEP
        return current


def _stream_result(clock) -> StreamGenerateResult:
    """One successful fake stream. The stamp is one read of the runner's clock."""
    return StreamGenerateResult(
        text="ok",
        metadata=dict(METADATA),
        chunk_count=FIXTURE_CHUNK_COUNT,
        first_content_at=clock(),
    )


class FakeAdapter(InferenceAdapter):
    """In-memory adapter. It never opens a socket."""

    def __init__(self, *, missing: bool = False, fail: bool = False) -> None:
        self.missing = missing
        self.fail = fail
        self.stream_calls = 0
        self.non_streaming_calls = 0
        self.show_calls = 0

    async def list_models(self) -> list[ModelInfo]:
        return []

    async def show_model(self, name: str) -> ModelInfo:
        self.show_calls += 1
        if self.missing:
            raise ModelNotInstalledError(name)
        return ModelInfo(
            name=name,
            size=None,
            quantization=None,
            parameter_size=None,
            raw={"name": name},
        )

    async def generate(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> GenerateResult:
        self.non_streaming_calls += 1
        raise AssertionError("the runner must not call non-streaming generate")

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.stream_calls += 1
        if self.fail:
            raise OllamaTimeoutError("Ollama request timed out")
        return _stream_result(clock)


class GatedAdapter(FakeAdapter):
    """Blocks measured stream calls until the test opens the gate.

    Warm-up yields once so overlapping warm-up calls would be visible, then
    returns. The gate starts closed.
    """

    def __init__(self, *, warmup_count: int, fail_measured: int | None = None) -> None:
        super().__init__()
        self.warmup_count = warmup_count
        self.fail_measured = fail_measured
        self.measured_calls = 0
        self.warmup_now = 0
        self.max_warmup = 0
        self.measured_now = 0
        self.max_measured = 0
        self.release = asyncio.Event()

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.stream_calls += 1
        if self.stream_calls <= self.warmup_count:
            self.warmup_now += 1
            self.max_warmup = max(self.max_warmup, self.warmup_now)
            try:
                await asyncio.sleep(0)
            finally:
                self.warmup_now -= 1
            return _stream_result(clock)

        self.measured_calls += 1
        this_measured = self.measured_calls
        self.measured_now += 1
        self.max_measured = max(self.max_measured, self.measured_now)
        try:
            await self.release.wait()
            if this_measured == self.fail_measured:
                raise OllamaTimeoutError("Ollama request timed out")
            return _stream_result(clock)
        finally:
            self.measured_now -= 1


class CancelAdapter(FakeAdapter):
    """Parks measured stream calls and sets the cancel signal once two are in flight."""

    def __init__(self, *, warmup_count: int, cancel_event: asyncio.Event) -> None:
        super().__init__()
        self.warmup_count = warmup_count
        self.cancel_event = cancel_event
        self.measured_calls = 0
        self._park = asyncio.Event()

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.stream_calls += 1
        if self.stream_calls <= self.warmup_count:
            return _stream_result(clock)
        self.measured_calls += 1
        if self.measured_calls >= 2:
            self.cancel_event.set()
        await self._park.wait()
        return _stream_result(clock)


def _runner(adapter: FakeAdapter) -> BenchmarkRunner:
    return BenchmarkRunner(adapter, clock=FakeClock())


@pytest.mark.asyncio
async def test_warmup_rows_are_excluded_from_measured() -> None:
    adapter = FakeAdapter()
    run = await _runner(adapter).run(
        "gemma3:1b",
        "Hi",
        num_predict=8,
        warmup_count=2,
        measured_count=3,
    )

    assert len(run.warmup) == 2
    assert {row.phase for row in run.warmup} == {"warmup"}
    assert {row.phase for row in run.measured} == {"measured"}
    assert all(row.phase != "warmup" for row in run.measured)
    assert adapter.non_streaming_calls == 0


@pytest.mark.asyncio
async def test_measured_length_equals_repetition_count() -> None:
    measured_count = 4
    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        num_predict=8,
        warmup_count=2,
        measured_count=measured_count,
        concurrency=1,
    )

    assert run.concurrency == 1
    assert len(run.measured) == measured_count
    assert run.measured[0].model == "gemma3:1b"
    assert run.measured[0].prompt == "Hi"
    assert run.measured[0].num_predict == 8


@pytest.mark.asyncio
async def test_end_to_end_duration_is_the_fake_clock_difference() -> None:
    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        warmup_count=2,
        measured_count=3,
        concurrency=1,
    )

    assert run.concurrency == 1
    for row in (*run.warmup, *run.measured):
        assert row.first_content_at is not None
        assert row.first_content_at - row.client_start == CLOCK_STEP
        assert row.client_end - row.first_content_at == CLOCK_STEP
        assert row.client_end - row.client_start == 2 * CLOCK_STEP
        clock_difference_ms = (row.client_end - row.client_start) * 1000.0
        assert row.end_to_end_ms == clock_difference_ms
        assert row.eval_duration == FIXTURE_EVAL_DURATION
        assert isinstance(row.eval_duration, int)
        assert row.prompt_eval_duration == FIXTURE_PROMPT_EVAL_DURATION
        assert isinstance(row.prompt_eval_duration, int)
        assert row.end_to_end_ms != row.eval_duration


@pytest.mark.asyncio
async def test_eval_count_stays_apart_from_chunk_count() -> None:
    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        warmup_count=1,
        measured_count=1,
    )

    row = run.measured[0]
    assert row.eval_count == FIXTURE_EVAL_COUNT
    assert row.eval_count != FIXTURE_CHUNK_COUNT
    assert "chunk_count" not in row.__dataclass_fields__


@pytest.mark.asyncio
async def test_missing_model_causes_zero_stream_calls() -> None:
    adapter = FakeAdapter(missing=True)
    runner = _runner(adapter)

    with pytest.raises(ModelNotInstalledError):
        await runner.run("missing:model", "Hi", warmup_count=2, measured_count=3)

    assert adapter.show_calls == 1
    assert adapter.stream_calls == 0
    assert adapter.non_streaming_calls == 0


@pytest.mark.asyncio
async def test_failed_stream_is_recorded_once() -> None:
    adapter = FakeAdapter(fail=True)
    run = await _runner(adapter).run(
        "gemma3:1b",
        "Hi",
        warmup_count=0,
        measured_count=1,
    )

    assert adapter.stream_calls == 1
    assert adapter.non_streaming_calls == 0
    assert len(run.measured) == 1
    row = run.measured[0]
    assert row.success is False
    assert row.error_type == "OllamaTimeoutError"
    assert row.first_content_at is None
    assert row.eval_count is None
    assert row.eval_duration is None


async def _wait_for_two_measured(adapter: GatedAdapter, task: asyncio.Task[object]) -> None:
    for _ in range(1000):
        if adapter.measured_now >= 2 or task.done():
            break
        await asyncio.sleep(0)
    else:
        pytest.fail("measured calls did not reach the cap")
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_measured_cap_of_two_limits_in_flight_calls() -> None:
    adapter = GatedAdapter(warmup_count=2)
    runner = BenchmarkRunner(adapter)
    task = asyncio.create_task(
        runner.run(
            "gemma3:1b",
            "Hi",
            num_predict=8,
            warmup_count=2,
            measured_count=4,
            concurrency=2,
        )
    )
    try:
        await _wait_for_two_measured(adapter, task)
        assert adapter.measured_now == 2
        assert adapter.max_measured == 2
        assert adapter.max_warmup == 1
        adapter.release.set()
        run = await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    assert run.concurrency == 2
    assert len(run.warmup) == 2
    assert {row.phase for row in run.warmup} == {"warmup"}
    assert len(run.measured) == 4
    assert all(row.phase == "measured" for row in run.measured)
    assert all(row.success and row.error_type is None for row in run.measured)
    assert adapter.max_measured == 2
    assert adapter.stream_calls == 6
    assert adapter.non_streaming_calls == 0


@pytest.mark.asyncio
async def test_cancel_signal_records_each_started_attempt_once() -> None:
    cancel_event = asyncio.Event()
    adapter = CancelAdapter(warmup_count=2, cancel_event=cancel_event)
    run = await asyncio.wait_for(
        BenchmarkRunner(adapter).run(
            "gemma3:1b",
            "Hi",
            warmup_count=2,
            measured_count=4,
            concurrency=2,
            cancel_event=cancel_event,
        ),
        timeout=2,
    )

    assert adapter.measured_calls == 2
    assert len(run.measured) == 2
    assert len(run.warmup) == 2
    assert all(row.phase == "warmup" and row.success for row in run.warmup)
    assert [row.error_type for row in run.measured] == ["CancelledError", "CancelledError"]
    assert all(row.success is False for row in run.measured)
    assert all(row.eval_count is None and row.eval_duration is None for row in run.measured)
    assert all(row.first_content_at is None for row in run.measured)
    assert adapter.stream_calls == 4
    assert adapter.non_streaming_calls == 0
    assert run.concurrency == 2


@pytest.mark.asyncio
async def test_failed_stream_does_not_cancel_other_measured_calls() -> None:
    adapter = GatedAdapter(warmup_count=1, fail_measured=1)
    runner = BenchmarkRunner(adapter)
    task = asyncio.create_task(
        runner.run(
            "gemma3:1b",
            "Hi",
            warmup_count=1,
            measured_count=4,
            concurrency=2,
        )
    )
    try:
        await _wait_for_two_measured(adapter, task)
        assert adapter.measured_now == 2
        adapter.release.set()
        run = await asyncio.wait_for(task, timeout=2)
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    assert adapter.stream_calls == 5
    assert adapter.non_streaming_calls == 0
    assert len(run.measured) == 4
    assert [row.error_type for row in run.measured].count("OllamaTimeoutError") == 1
    assert all(row.error_type != "CancelledError" for row in run.measured)
    failed = [row for row in run.measured if row.error_type == "OllamaTimeoutError"]
    assert failed[0].success is False
    assert failed[0].first_content_at is None
    assert failed[0].eval_count is None
    assert failed[0].eval_duration is None
    succeeded = [row for row in run.measured if row.success]
    assert len(succeeded) == 3
    assert all(row.first_content_at is not None for row in succeeded)


def test_runner_and_adapter_expose_no_percentile_ttft_or_tpot_helper() -> None:
    import app.benchmark.runner as runner_module
    import app.inference.base as base_module
    import app.inference.ollama as ollama_module
    import app.metrics.latency as latency_module

    banned = ("percentile", "ttft", "tpot", "throughput")
    names = [name.lower() for name in dir(BenchmarkRunner)]
    names.extend(name.lower() for name in dir(OllamaAdapter))
    names.extend(name.lower() for name in dir(InferenceAdapter))
    for module in (runner_module, ollama_module, base_module):
        names.extend(name.lower() for name in dir(module))
    for name in names:
        for word in banned:
            assert word not in name
    assert callable(latency_module.ttft_ms)
    assert callable(latency_module.decode_duration_ms)
    assert callable(latency_module.tpot_ms)
