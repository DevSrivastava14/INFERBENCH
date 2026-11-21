"""Async Ollama client.

Talks to ``GET /api/tags``, ``POST /api/show``, and ``POST /api/generate``.
Server duration fields are kept on the raw metadata object. This module does
not convert them, and it does not compute TTFT, TPOT, throughput, or percentiles.
One attempt per call. No retries.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import OllamaConfig
from app.core.exceptions import (
    MalformedResponseError,
    ModelNotInstalledError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.inference.base import (
    GenerateOptions,
    GenerateResult,
    InferenceAdapter,
    ModelInfo,
    StreamGenerateResult,
)


class OllamaAdapter(InferenceAdapter):
    """httpx client for a local Ollama server."""

    def __init__(
        self,
        config: OllamaConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config if config is not None else OllamaConfig.from_env()
        self._transport = transport

    async def list_models(self) -> list[ModelInfo]:
        body = await self._request("GET", "/api/tags")
        models = body.get("models")
        if not isinstance(models, list):
            raise MalformedResponseError("tags response has no models list")
        return [_model_info(item) for item in models]

    async def show_model(self, name: str) -> ModelInfo:
        body = await self._request("POST", "/api/show", json_body={"model": name}, model=name)
        return _model_info(body, fallback_name=name)

    async def generate(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> GenerateResult:
        payload = _generate_body(model, prompt, options, stream=False)
        body = await self._request("POST", "/api/generate", json_body=payload, model=model)
        text = body.get("response")
        if not isinstance(text, str):
            raise MalformedResponseError("generate response has no text")
        return GenerateResult(text=text, metadata=body)

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock: Callable[[], float],
    ) -> StreamGenerateResult:
        payload = _generate_body(model, prompt, options, stream=True)
        parts: list[str] = []
        metadata: dict[str, Any] | None = None
        chunk_count = 0
        first_content_at: float | None = None
        try:
            async with self._client() as client:
                async with client.stream("POST", "/api/generate", json=payload) as response:
                    if response.status_code >= 400:
                        raw = await response.aread()
                        _raise_for_status(response.status_code, raw, model=model)
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        obj = _json_object(line.encode())
                        piece = obj.get("response", "")
                        if not isinstance(piece, str):
                            raise MalformedResponseError("stream chunk response is not text")
                        parts.append(piece)
                        metadata = obj
                        chunk_count += 1
                        if piece != "" and first_content_at is None:
                            first_content_at = clock()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama request timed out") from exc
        except httpx.NetworkError as exc:
            raise OllamaUnavailableError("Ollama is unavailable") from exc
        except httpx.InvalidURL as exc:
            raise OllamaUnavailableError("Ollama base URL is invalid") from exc

        if metadata is None:
            raise MalformedResponseError("generate stream contained no JSON objects")
        return StreamGenerateResult(
            text="".join(parts),
            metadata=metadata,
            chunk_count=chunk_count,
            first_content_at=first_content_at,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.request(method, path, json=json_body)
                raw = await response.aread()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama request timed out") from exc
        except httpx.NetworkError as exc:
            raise OllamaUnavailableError("Ollama is unavailable") from exc
        except httpx.InvalidURL as exc:
            raise OllamaUnavailableError("Ollama base URL is invalid") from exc
        _raise_for_status(response.status_code, raw, model=model)
        return _json_object(raw)

    def _client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(self._config.timeout_seconds)
        return httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=timeout,
            transport=self._transport,
        )


def _generate_body(
    model: str,
    prompt: str,
    options: GenerateOptions | None,
    *,
    stream: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {"model": model, "prompt": prompt, "stream": stream}
    if options is not None and options.num_predict is not None:
        body["options"] = {"num_predict": options.num_predict}
    return body


def _model_info(payload: Any, *, fallback_name: str | None = None) -> ModelInfo:
    if not isinstance(payload, dict):
        raise MalformedResponseError("model entry is not an object")
    name = payload.get("name") or payload.get("model") or fallback_name
    if not isinstance(name, str) or not name:
        raise MalformedResponseError("model entry has no name")
    size = _optional_int(payload.get("size"), "model size")
    quantization, parameter_size = _detail_strings(payload.get("details"))
    return ModelInfo(
        name=name,
        size=size,
        quantization=quantization,
        parameter_size=parameter_size,
        raw=payload,
    )


def _detail_strings(details: Any) -> tuple[str | None, str | None]:
    if details is None:
        return None, None
    if not isinstance(details, dict):
        raise MalformedResponseError("model details is not an object")
    quantization = details.get("quantization_level")
    parameter_size = details.get("parameter_size")
    if quantization is not None and not isinstance(quantization, str):
        raise MalformedResponseError("quantization_level is not a string")
    if parameter_size is not None and not isinstance(parameter_size, str):
        raise MalformedResponseError("parameter_size is not a string")
    return quantization, parameter_size


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedResponseError(f"{label} is not an integer")
    return value


def _json_object(raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MalformedResponseError("Ollama response is not JSON") from exc
    if not isinstance(data, dict):
        raise MalformedResponseError("Ollama response is not a JSON object")
    return data


def _raise_for_status(status_code: int, raw: bytes, *, model: str | None) -> None:
    if status_code < 400:
        return
    if status_code == 404 and model is not None:
        raise ModelNotInstalledError(model)
    detail = _error_text(raw)
    message = f"Ollama returned HTTP {status_code}"
    if detail:
        message = f"{message}: {detail}"
    raise MalformedResponseError(message)


def _error_text(raw: bytes) -> str | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        text = raw.decode("utf-8", errors="replace").strip()
        return text or None
    if isinstance(data, dict) and isinstance(data.get("error"), str):
        return data["error"]
    return None
