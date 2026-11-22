"""Four frozen workload profiles.

The caller passes the prompt, ``num_predict``, and the profile name into
the runner. This module does not call Ollama and does not start a run.
"""

from __future__ import annotations

from dataclasses import dataclass

SHORT_PROMPT = "Name one fact about local inference."
FILLER_SENTENCE = "This sentence only makes the prompt longer. "
LONG_PROMPT = SHORT_PROMPT + " " + (FILLER_SENTENCE * 30)

SHORT_OUTPUT = 32
LONG_OUTPUT = 128


@dataclass(frozen=True)
class WorkloadProfile:
    """One named prompt and output cap.

    ``num_predict`` is the cap sent with the call. It is not a token count.
    """

    name: str
    prompt: str
    num_predict: int


PROFILES: tuple[WorkloadProfile, ...] = (
    WorkloadProfile("short_prompt_short_output", SHORT_PROMPT, SHORT_OUTPUT),
    WorkloadProfile("long_prompt_short_output", LONG_PROMPT, SHORT_OUTPUT),
    WorkloadProfile("short_prompt_long_output", SHORT_PROMPT, LONG_OUTPUT),
    WorkloadProfile("long_prompt_long_output", LONG_PROMPT, LONG_OUTPUT),
)
