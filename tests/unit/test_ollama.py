"""Ollama adapter tests. Every response comes from an httpx mock transport.

Ollama is not contacted. Duration integers in these fixtures are raw provider
fields on the mock body. No test asserts a latency measurement.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.exceptions import (
    MalformedResponseError,
    ModelNotInstalledError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.inference.base import GenerateOptions, InferenceAdapter
from app.inference.ollama import OllamaAdapter

TAGS_MODEL = {
    "name": "gemma3:1b",
    "model": "gemma3:1b",
    "size": 806,
    "details": {
        "parameter_size": "999.89M",
        "quantization_level": "Q4_K_M",
    },
}

SHOW_MODEL = {
    "name": "qwen3.5:2b",
    "size": 2683,
    "details": {
        "parameter_size": "1.9B",
        "quantization_level": "Q8_0",
    },
}

GENERATE_BODY = {
    "model": "gemma3:1b",
    "response": "Hello",
    "done": True,
    "eval_count": 2,
    "prompt_eval_count": 1,
    "prompt_eval_duration": 10,
    "eval_duration": 20,
}


def _adapter(handler) -> OllamaAdapter:
    return OllamaAdapter(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_tags_parses_name_size_quantization_and_parameter_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [TAGS_MODEL]})

    models = await _adapter(handler).list_models()

    assert len(models) == 1
    info = models[0]
    assert info.name == "gemma3:1b"
    assert info.size == 806
    assert info.quantization == "Q4_K_M"
    assert info.parameter_size == "999.89M"
    assert info.architecture is None
    assert info.raw == TAGS_MODEL


@pytest.mark.asyncio
async def test_show_parses_name_size_quantization_and_parameter_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/show"
        assert json.loads(request.content) == {"model": "qwen3.5:2b"}
        return httpx.Response(200, json=SHOW_MODEL)

    info = await _adapter(handler).show_model("qwen3.5:2b")

    assert info.name == "qwen3.5:2b"
    assert info.size == 2683
    assert info.quantization == "Q8_0"
    assert info.parameter_size == "1.9B"
    assert info.architecture is None
    assert info.raw == SHOW_MODEL


@pytest.mark.asyncio
async def test_connection_failure_is_unavailable() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused")

    with pytest.raises(OllamaUnavailableError):
        await _adapter(handler).list_models()

    assert calls == 1


@pytest.mark.asyncio
async def test_unknown_model_is_not_installed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'missing:model' not found"})

    with pytest.raises(ModelNotInstalledError) as exc_info:
        await _adapter(handler).show_model("missing:model")

    assert exc_info.value.model == "missing:model"


@pytest.mark.asyncio
async def test_malformed_body_is_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(MalformedResponseError):
        await _adapter(handler).list_models()


@pytest.mark.asyncio
async def test_timeout_is_timeout_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(OllamaTimeoutError):
        await _adapter(handler).list_models()

    assert calls == 1


@pytest.mark.asyncio
async def test_generate_returns_text_and_raw_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        body = json.loads(request.content)
        assert body["model"] == "gemma3:1b"
        assert body["prompt"] == "Hi"
        assert body["stream"] is False
        assert "think" not in body
        assert body["options"] == {"num_predict": 8}
        return httpx.Response(200, json=GENERATE_BODY)

    result = await _adapter(handler).generate(
        "gemma3:1b",
        "Hi",
        GenerateOptions(num_predict=8),
    )

    assert result.text == "Hello"
    assert result.metadata == GENERATE_BODY
    assert result.metadata["eval_count"] == 2
    assert result.metadata["prompt_eval_count"] == 1


@pytest.mark.asyncio
async def test_stream_chunk_count_stays_apart_from_eval_count() -> None:
    lines = [
        {"response": "a", "done": False},
        {"response": "b", "done": False},
        {"response": "c", "done": False},
        {
            "response": "",
            "done": True,
            "eval_count": 2,
            "prompt_eval_count": 1,
            "prompt_eval_duration": 10,
            "eval_duration": 20,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        assert "think" not in body
        assert body["options"] == {"num_predict": 8}
        raw = "\n".join(json.dumps(line) for line in lines).encode()
        return httpx.Response(200, content=raw)

    def clock() -> float:
        return 1.0

    result = await _adapter(handler).generate_stream(
        "gemma3:1b",
        "Hi",
        GenerateOptions(num_predict=8),
        clock=clock,
    )

    assert result.text == "abc"
    assert result.chunk_count == 4
    assert result.metadata["eval_count"] == 2
    assert result.chunk_count != result.metadata["eval_count"]


@pytest.mark.asyncio
async def test_leading_empty_response_stamps_the_later_piece(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed = 0
    original_loads = json.loads

    def loads(raw, *args, **kwargs):
        nonlocal parsed
        parsed += 1
        return original_loads(raw, *args, **kwargs)

    monkeypatch.setattr("app.inference.ollama.json.loads", loads)
    stamped_at_object: list[int] = []

    def clock() -> float:
        stamped_at_object.append(parsed)
        return 4.0

    lines = [
        {"response": "", "done": False},
        {"response": "later", "done": False},
        {
            "response": "",
            "done": True,
            "eval_count": 2,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        payload = "\n".join(json.dumps(line) for line in lines)
        return httpx.Response(200, content=f"\n{payload}\n".encode())

    result = await _adapter(handler).generate_stream(
        "gemma3:1b",
        "Hi",
        clock=clock,
    )

    assert result.text == "later"
    assert result.chunk_count == 3
    assert stamped_at_object == [2]
    assert result.first_content_at == 4.0


@pytest.mark.asyncio
async def test_generate_sends_think_false_beside_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "qwen3.5:2b"
        assert body["stream"] is False
        assert body["think"] is False
        assert body["options"] == {"num_predict": 32}
        return httpx.Response(200, json=GENERATE_BODY)

    result = await _adapter(handler).generate(
        "qwen3.5:2b",
        "Hi",
        GenerateOptions(num_predict=32, think=False),
    )

    assert result.text == "Hello"
    assert result.metadata["eval_count"] == 2


@pytest.mark.asyncio
async def test_generate_sends_num_thread_beside_num_predict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "gemma3:1b"
        assert body["stream"] is False
        assert "think" not in body
        assert body["options"] == {"num_predict": 32, "num_thread": 4}
        return httpx.Response(200, json=GENERATE_BODY)

    result = await _adapter(handler).generate(
        "gemma3:1b",
        "Hi",
        GenerateOptions(num_predict=32, num_thread=4),
    )

    assert result.text == "Hello"
    assert result.metadata["eval_count"] == 2


@pytest.mark.asyncio
async def test_generate_sends_think_false_and_num_thread_beside_num_predict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "qwen3.5:2b"
        assert body["stream"] is False
        assert body["think"] is False
        assert body["options"] == {"num_predict": 32, "num_thread": 4}
        return httpx.Response(200, json=GENERATE_BODY)

    result = await _adapter(handler).generate(
        "qwen3.5:2b",
        "Hi",
        GenerateOptions(num_predict=32, think=False, num_thread=4),
    )

    assert result.text == "Hello"
    assert result.metadata["eval_count"] == 2


@pytest.mark.asyncio
async def test_show_uses_details_family_when_it_is_a_string() -> None:
    payload = {
        "name": "qwen3.5:2b",
        "size": 2683,
        "details": {
            "family": "qwen35",
            "parameter_size": "1.9B",
            "quantization_level": "Q8_0",
        },
        "model_info": {"general.architecture": "other"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    info = await _adapter(handler).show_model("qwen3.5:2b")

    assert info.architecture == "qwen35"
    assert info.quantization == "Q8_0"
    assert info.parameter_size == "1.9B"
    assert info.size == 2683


@pytest.mark.asyncio
async def test_show_uses_general_architecture_when_family_is_not_a_string() -> None:
    payload = {
        "name": "gemma3:1b",
        "size": 806,
        "details": {
            "family": 1,
            "parameter_size": "999.89M",
            "quantization_level": "Q4_K_M",
        },
        "model_info": {"general.architecture": "gemma3"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    info = await _adapter(handler).show_model("gemma3:1b")

    assert info.architecture == "gemma3"


@pytest.mark.asyncio
async def test_engine_version_returns_the_version_string() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/version"
        return httpx.Response(200, json={"version": "0.test"})

    version = await _adapter(handler).engine_version()

    assert version == "0.test"


@pytest.mark.asyncio
async def test_engine_version_rejects_a_body_without_a_version_string() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    with pytest.raises(MalformedResponseError):
        await _adapter(handler).engine_version()


@pytest.mark.asyncio
async def test_engine_version_rejects_a_non_json_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        assert _request.url.path == "/api/version"
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(MalformedResponseError):
        await _adapter(handler).engine_version()


@pytest.mark.asyncio
async def test_engine_version_records_a_connection_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(OllamaUnavailableError):
        await _adapter(handler).engine_version()


def test_adapter_exposes_no_percentile_ttft_or_tpot_helper() -> None:
    banned = ("percentile", "ttft", "tpot", "throughput")
    names = [name.lower() for name in dir(OllamaAdapter)]
    names.extend(name.lower() for name in dir(InferenceAdapter))
    for name in names:
        for word in banned:
            assert word not in name
