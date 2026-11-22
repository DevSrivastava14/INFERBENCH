"""Benchmark tests. The adapter is a fake.

Ollama is not contacted. Clock values and duration integers are fixtures.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

from app.benchmark.runner import BenchmarkRunner
from app.benchmark.workload import PROFILES
from app.core.exceptions import ModelNotInstalledError, OllamaTimeoutError
from app.monitoring.sampler import ResourceSample
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

    async def engine_version(self) -> str:
        raise AssertionError("the runner must not call engine_version")

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


class PromptAdapter(FakeAdapter):
    """Records the prompt and ``num_predict`` sent on each stream call."""

    def __init__(self) -> None:
        super().__init__()
        self.prompts: list[str] = []
        self.num_predicts: list[int | None] = []

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.prompts.append(prompt)
        self.num_predicts.append(None if options is None else options.num_predict)
        return await super().generate_stream(model, prompt, options, clock=clock)


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


class SamplingAdapter(FakeAdapter):
    """Lets the sample loop take one sample inside each stream call.

    The first sample is taken after ``show_model`` and before the first
    stream call. Each later sample is taken while that call is still running.
    """

    def __init__(self, *, warmup_count: int) -> None:
        super().__init__()
        self.warmup_count = warmup_count
        self.events: list[str] = []
        self.seen: list[str] = []
        self.release_sample = asyncio.Event()

    async def show_model(self, name: str) -> ModelInfo:
        self.events.append("show")
        return await super().show_model(name)

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.stream_calls += 1
        phase = "warmup" if self.stream_calls <= self.warmup_count else "measured"
        self.events.append(phase)
        before = len(self.seen)
        self.release_sample.set()
        for _ in range(1000):
            if len(self.seen) > before:
                break
            await asyncio.sleep(0)
        else:
            pytest.fail("sampler did not run during the stream call")
        return _stream_result(clock)


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
    assert run.profile_name is None


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


def _fixture_sample(taken_at: float) -> ResourceSample:
    """One fake sample. The percent and byte counts are probe fixtures."""

    return ResourceSample(
        taken_at=taken_at,
        cpu_percent=0.0,
        system_ram_used_bytes=11,
        system_ram_total_bytes=22,
        process_rss_bytes=33,
    )


@pytest.mark.asyncio
async def test_fake_sampler_records_ordered_samples_after_show_model() -> None:
    adapter = SamplingAdapter(warmup_count=1)

    def sampler() -> ResourceSample:
        assert adapter.show_calls == 1
        if adapter.stream_calls == 0:
            label = "after-show"
        elif adapter.stream_calls <= adapter.warmup_count:
            label = "warmup"
        else:
            label = "measured"
        adapter.seen.append(label)
        return _fixture_sample(float(len(adapter.seen)))

    async def sleep(_interval: float) -> None:
        await adapter.release_sample.wait()
        adapter.release_sample.clear()

    run = await asyncio.wait_for(
        _runner(adapter).run(
            "gemma3:1b",
            "Hi",
            warmup_count=1,
            measured_count=1,
            sampler=sampler,
            sample_interval=0.5,
            sleep=sleep,
        ),
        timeout=2,
    )

    assert adapter.events == ["show", "warmup", "measured"]
    assert adapter.seen == ["after-show", "warmup", "measured"]
    assert [sample.taken_at for sample in run.resource_samples] == [1.0, 2.0, 3.0]
    assert run.sampling_error is None
    assert len(run.warmup) == 1
    assert len(run.measured) == 1


@pytest.mark.asyncio
async def test_run_without_sampler_records_no_samples() -> None:
    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        warmup_count=1,
        measured_count=1,
    )

    assert run.resource_samples == ()
    assert run.sampling_error is None


@pytest.mark.asyncio
async def test_missing_model_takes_no_sample() -> None:
    adapter = FakeAdapter(missing=True)
    taken: list[ResourceSample] = []

    def sampler() -> ResourceSample:
        sample = _fixture_sample(1.0)
        taken.append(sample)
        return sample

    async def sleep(_interval: float) -> None:
        await asyncio.sleep(0)

    with pytest.raises(ModelNotInstalledError):
        await _runner(adapter).run(
            "missing:model",
            "Hi",
            warmup_count=1,
            measured_count=1,
            sampler=sampler,
            sleep=sleep,
        )

    assert taken == []
    assert adapter.show_calls == 1
    assert adapter.stream_calls == 0


@pytest.mark.asyncio
async def test_later_sampler_failure_keeps_earlier_samples_and_rows() -> None:
    calls: list[int] = []

    def sampler() -> ResourceSample:
        calls.append(len(calls) + 1)
        if len(calls) >= 2:
            raise RuntimeError("probe failed")
        return _fixture_sample(float(calls[-1]))

    async def sleep(_interval: float) -> None:
        return

    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        warmup_count=1,
        measured_count=1,
        sampler=sampler,
        sleep=sleep,
    )

    assert calls == [1, 2]
    assert run.resource_samples == (_fixture_sample(1.0),)
    assert run.sampling_error == "RuntimeError"
    assert len(run.warmup) == 1
    assert len(run.measured) == 1
    assert run.measured[0].success is True


@pytest.mark.asyncio
async def test_cancelled_run_keeps_samples_and_skips_unstarted_calls() -> None:
    cancel_event = asyncio.Event()
    adapter = CancelAdapter(warmup_count=1, cancel_event=cancel_event)
    taken: list[ResourceSample] = []

    def sampler() -> ResourceSample:
        assert adapter.show_calls == 1
        sample = _fixture_sample(float(len(taken) + 1))
        taken.append(sample)
        return sample

    async def sleep(_interval: float) -> None:
        await asyncio.Event().wait()

    run = await asyncio.wait_for(
        BenchmarkRunner(adapter, clock=FakeClock()).run(
            "gemma3:1b",
            "Hi",
            warmup_count=1,
            measured_count=4,
            concurrency=2,
            cancel_event=cancel_event,
            sampler=sampler,
            sleep=sleep,
        ),
        timeout=2,
    )

    assert taken == [_fixture_sample(1.0)]
    assert run.resource_samples == (_fixture_sample(1.0),)
    assert run.sampling_error is None
    assert adapter.measured_calls == 2
    assert len(run.measured) == 2
    assert [row.error_type for row in run.measured] == ["CancelledError", "CancelledError"]


@pytest.mark.asyncio
async def test_long_prompt_short_output_stores_the_name_and_sends_cap_32() -> None:
    import app.benchmark.runner as runner_module

    profile = next(item for item in PROFILES if item.name == "long_prompt_short_output")
    adapter = PromptAdapter()
    run = await _runner(adapter).run(
        "gemma3:1b",
        profile.prompt,
        num_predict=profile.num_predict,
        profile_name=profile.name,
        warmup_count=1,
        measured_count=1,
    )

    assert profile.num_predict == 32
    assert run.profile_name == "long_prompt_short_output"
    assert adapter.prompts == [profile.prompt, profile.prompt]
    assert adapter.num_predicts == [32, 32]
    assert all(row.prompt == profile.prompt for row in run.warmup + run.measured)
    assert all(row.num_predict == 32 for row in run.warmup + run.measured)
    assert "workload" not in vars(runner_module)


def test_metrics_exposes_no_sampler_or_database() -> None:
    import app.metrics as metrics_package
    import app.metrics.latency as latency_module
    import app.metrics.statistics as statistics_module
    import app.metrics.throughput as throughput_module

    banned = ("sampler", "psutil", "sqlalchemy", "sqlite", "database")
    names: list[str] = []
    for module in (metrics_package, latency_module, statistics_module, throughput_module):
        names.extend(name.lower() for name in dir(module))
    for name in names:
        for word in banned:
            assert word not in name


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
