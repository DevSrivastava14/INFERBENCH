"""Adapter operations shared by inference providers.

The four operations are list models, show one model, generate, and generate
stream. Results carry provider text and raw provider metadata. They do not
carry TTFT, TPOT, throughput, or percentiles.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelInfo:
    """Fields parsed from one model payload, plus the raw object."""

    name: str
    size: int | None
    quantization: str | None
    parameter_size: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class GenerateOptions:
    """The small options object accepted by a generate call.

    ``num_predict`` caps how many tokens the server may generate. When it is
    omitted, the adapter does not send an options object.
    """

    num_predict: int | None = None


@dataclass(frozen=True)
class GenerateResult:
    """Non-streaming generate: text, and the raw final provider object."""

    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class StreamGenerateResult:
    """Streaming generate.

    ``text`` is the joined ``response`` pieces. ``metadata`` is the last
    provider object. ``chunk_count`` is the number of JSON lines. It is not
    ``eval_count`` and it is not a token count.
    """

    text: str
    metadata: dict[str, Any]
    chunk_count: int


class InferenceAdapter(ABC):
    """Discovery and generation. No metric helpers."""

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return the models the provider reports."""

    @abstractmethod
    async def show_model(self, name: str) -> ModelInfo:
        """Return one model's provider metadata."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> GenerateResult:
        """One non-streaming generate call."""

    @abstractmethod
    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> StreamGenerateResult:
        """One streaming generate call, read to completion."""
