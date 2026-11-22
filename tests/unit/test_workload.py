"""Workload profile catalog.

The profiles are frozen strings and caps. Ollama is not contacted. No test
asserts a live latency.
"""

from __future__ import annotations

from app.benchmark.workload import (
    FILLER_SENTENCE,
    LONG_PROMPT,
    PROFILES,
    SHORT_PROMPT,
)

EXPECTED_NAMES = (
    "short_prompt_short_output",
    "long_prompt_short_output",
    "short_prompt_long_output",
    "long_prompt_long_output",
)


def test_profile_names_follow_the_catalog_order() -> None:
    assert tuple(profile.name for profile in PROFILES) == EXPECTED_NAMES


def test_short_prompts_match_and_long_prompts_are_longer() -> None:
    short_a, long_a, short_b, long_b = PROFILES

    assert short_a.prompt == short_b.prompt == SHORT_PROMPT
    assert long_a.prompt == long_b.prompt == LONG_PROMPT
    assert LONG_PROMPT == SHORT_PROMPT + " " + (FILLER_SENTENCE * 30)
    assert len(LONG_PROMPT) > len(SHORT_PROMPT)


def test_short_output_cap_is_32_and_long_output_cap_is_128() -> None:
    assert tuple(profile.num_predict for profile in PROFILES) == (32, 32, 128, 128)
