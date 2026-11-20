"""Sequential benchmark tests. The adapter is a fake.

Ollama is not contacted. Clock values and duration integers are fixtures.
No test asserts a latency number from a live server.
"""

from __future__ import annotations

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


class FakeAdapter(InferenceAdapter):
    """In-memory adapter. It never opens a socket."""

    def __init__(self, *, missing: bool = False, fail: bool = False) -> None:
        self.missing = missing
        self.fail = fail
        self.generate_calls = 0
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
        self.generate_calls += 1
        if self.fail:
            raise OllamaTimeoutError("Ollama request timed out")
        return GenerateResult(text="ok", metadata=dict(METADATA))

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> StreamGenerateResult:
        raise AssertionError("the sequential runner must not stream")


def _runner(adapter: FakeAdapter) -> BenchmarkRunner:
    return BenchmarkRunner(adapter, clock=FakeClock())


@pytest.mark.asyncio
async def test_warmup_rows_are_excluded_from_measured() -> None:
    run = await _runner(FakeAdapter()).run(
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


@pytest.mark.asyncio
async def test_measured_length_equals_repetition_count() -> None:
    measured_count = 4
    run = await _runner(FakeAdapter()).run(
        "gemma3:1b",
        "Hi",
        num_predict=8,
        warmup_count=2,
        measured_count=measured_count,
    )

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
    )

    for row in run.measured:
        clock_difference_ms = (row.client_end - row.client_start) * 1000.0
        assert row.end_to_end_ms == clock_difference_ms
        assert row.client_end - row.client_start == CLOCK_STEP
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
async def test_missing_model_causes_zero_generate_calls() -> None:
    adapter = FakeAdapter(missing=True)
    runner = _runner(adapter)

    with pytest.raises(ModelNotInstalledError):
        await runner.run("missing:model", "Hi", warmup_count=2, measured_count=3)

    assert adapter.show_calls == 1
    assert adapter.generate_calls == 0


@pytest.mark.asyncio
async def test_failed_generate_is_recorded_once() -> None:
    adapter = FakeAdapter(fail=True)
    run = await _runner(adapter).run(
        "gemma3:1b",
        "Hi",
        warmup_count=0,
        measured_count=1,
    )

    assert adapter.generate_calls == 1
    assert len(run.measured) == 1
    row = run.measured[0]
    assert row.success is False
    assert row.error_type == "OllamaTimeoutError"
    assert row.eval_count is None
    assert row.eval_duration is None


def test_runner_and_adapter_expose_no_percentile_ttft_or_tpot_helper() -> None:
    banned = ("percentile", "ttft", "tpot", "throughput")
    names = [name.lower() for name in dir(BenchmarkRunner)]
    names.extend(name.lower() for name in dir(OllamaAdapter))
    names.extend(name.lower() for name in dir(InferenceAdapter))
    for name in names:
        for word in banned:
            assert word not in name
