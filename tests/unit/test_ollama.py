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
        assert body["options"] == {"num_predict": 8}
        raw = "\n".join(json.dumps(line) for line in lines).encode()
        return httpx.Response(200, content=raw)

    result = await _adapter(handler).generate_stream(
        "gemma3:1b",
        "Hi",
        GenerateOptions(num_predict=8),
    )

    assert result.text == "abc"
    assert result.chunk_count == 4
    assert result.metadata["eval_count"] == 2
    assert result.chunk_count != result.metadata["eval_count"]


def test_adapter_exposes_no_percentile_ttft_or_tpot_helper() -> None:
    banned = ("percentile", "ttft", "tpot", "throughput")
    names = [name.lower() for name in dir(OllamaAdapter)]
    names.extend(name.lower() for name in dir(InferenceAdapter))
    for name in names:
        for word in banned:
            assert word not in name
