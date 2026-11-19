"""Failures the Ollama adapter keeps apart.

There is no retry. Each call either returns or raises one of these errors.
"""


class OllamaError(Exception):
    """Base for a single failed Ollama call."""


class OllamaUnavailableError(OllamaError):
    """The connection failed, or the server did not answer."""


class ModelNotInstalledError(OllamaError):
    """The server answered, and the named model is absent."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(f"model is not installed: {model}")


class MalformedResponseError(OllamaError):
    """The body is not the JSON object the adapter expects."""


class OllamaTimeoutError(OllamaError):
    """The wait exceeded the limit set for the call."""
