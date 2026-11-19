"""Ollama connection settings.

The base URL defaults to the local Ollama server. ``OLLAMA_HOST`` may be a
host and port with no scheme; that value is turned into an ``http`` base URL.
This module does not time requests or compute metrics.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT_SECONDS = 120.0


def normalize_base_url(host: str | None) -> str:
    """Return a base URL. A value with no scheme receives ``http://``."""
    if host is None:
        return DEFAULT_BASE_URL
    value = host.strip()
    if not value:
        return DEFAULT_BASE_URL
    if "://" not in value:
        value = "http://" + value
    return value.rstrip("/")


@dataclass(frozen=True)
class OllamaConfig:
    """Where the adapter sends HTTP, and how long one call may wait.

    ``timeout_seconds`` is a client limit for a single request. It is not a
    benchmark measurement. The adapter does not retry when the limit is hit.
    """

    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> OllamaConfig:
        """Build a config from ``OLLAMA_HOST``. An absent value uses the default."""
        env = os.environ if environ is None else environ
        return cls(base_url=normalize_base_url(env.get("OLLAMA_HOST")))
