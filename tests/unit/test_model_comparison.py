"""Checks in the model-comparison script. No live server.

The script module is loaded here. Pytest does not collect that script, and
this file does not read ``docs/model-findings.md``. Clock values and token
counts below are fixtures. No test asserts a latency number from a live server.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.database.repository import StoredExperiment
from app.inference.base import ModelInfo
from app.benchmark.records import RequestRecord
from app.metrics.statistics import AggregateSummary
from app.monitoring.sampler import ResourceSample
from app.monitoring.snapshot import ConfigurationSnapshot

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_model_comparison.py"
_SPEC = importlib.util.spec_from_file_location("run_model_comparison", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _info(
    name: str,
    *,
    architecture: str | None,
    quantization: str | None,
    size: int | None = None,
) -> ModelInfo:
    return ModelInfo(
        name=name,
        size=size,
        quantization=quantization,
        parameter_size=None,
        raw={"name": name},
        architecture=architecture,
    )


def test_cloud_tags_stay_out_of_the_quantization_check() -> None:
    models = [
        _info("local:one", architecture="family", quantization="Q4"),
        _info("gemma4:31b-cloud", architecture="family", quantization="Q8"),
        _info("deepseek-v4.1-flash:cloud", architecture="family", quantization="Q5"),
    ]

    assert _MODULE._quantization_pair(models) is None


def test_same_architecture_and_different_quantization_is_a_pair() -> None:
    left = _info("local:one", architecture="family", quantization="Q4")
    right = _info("local:two", architecture="family", quantization="Q8")

    assert _MODULE._quantization_pair([left, right]) == (left, right)


def test_different_architectures_are_not_a_quantization_pair() -> None:
    models = [
        _info("local:one", architecture="alpha", quantization="Q8"),
        _info("local:two", architecture="beta", quantization="Q4"),
    ]

    assert _MODULE._quantization_pair(models) is None


def test_missing_architecture_is_not_a_quantization_pair() -> None:
    models = [
        _info("local:one", architecture=None, quantization="Q8"),
        _info("local:two", architecture=None, quantization="Q4"),
    ]

    assert _MODULE._quantization_pair(models) is None


def test_show_size_gap_is_filled_from_tags() -> None:
    shown = _info("local:one", architecture="alpha", quantization="Q8", size=None)
    tag = _info("local:one", architecture=None, quantization=None, size=11)

    merged = _MODULE._metadata(shown, tag)

    assert merged.size == 11
    assert merged.quantization == "Q8"
    assert merged.architecture == "alpha"


def test_metadata_stays_unset_when_show_and_tags_omit_it() -> None:
    shown = _info("local:one", architecture=None, quantization=None, size=None)

    merged = _MODULE._metadata(shown, None)

    assert merged.size is None
    assert merged.quantization is None
    assert merged.architecture is None


def test_findings_use_fixture_rows_and_state_the_limits() -> None:
    text = _MODULE._findings((_stored(think=False), _stored(think=None)))

    assert "This file is a cross-model comparison." in text
    assert "Experiment G was not run." in text
    assert "Thinking on versus off was not run." in text
    assert "It does not recommend a model." in text
    assert "The request timeout was the adapter default of 120 seconds." in text
    assert "The measured count is 3." in text
    assert "Think: false" in text
    assert "Think: null" in text
    assert "Architecture: not present" in text
    assert "prompt_eval_count 4" in text
    assert "eval_count 3" in text
    assert "TTFT 500" in text
    assert "TPOT 250" in text
    assert "error_type unset" in text
    assert "Min system CPU percent: 0" in text


def _stored(*, think: bool | None) -> StoredExperiment:
    row = RequestRecord(
        phase="measured",
        model="local:one",
        prompt="fixture",
        num_predict=32,
        client_start=1.0,
        first_content_at=1.5,
        client_end=2.0,
        end_to_end_ms=1000.0,
        success=True,
        error_type=None,
        eval_count=3,
        prompt_eval_count=4,
        prompt_eval_duration=None,
        eval_duration=None,
    )
    snapshot = ConfigurationSnapshot(
        model="local:one",
        prompt="fixture",
        num_predict=32,
        warmup_count=2,
        measured_count=3,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.fixture",
        capture_time=1.0,
        cpu_model="fixture-cpu",
        logical_cpu_count=2,
        total_ram_bytes=8,
        python_version="3.x",
        profile_name="short_prompt_short_output",
        think=think,
        quantization="Q-fixture",
        parameter_size="1B",
        model_size_bytes=11,
        architecture=None,
    )
    return StoredExperiment(
        experiment_id=1,
        snapshot=snapshot,
        warmup=(),
        measured=(row,),
        resource_samples=(
            ResourceSample(
                taken_at=1.0,
                cpu_percent=0.0,
                system_ram_used_bytes=5,
                system_ram_total_bytes=8,
                process_rss_bytes=1,
            ),
        ),
        sampling_error=None,
        summary=AggregateSummary(
            average_ms=1000.0,
            median_ms=1000.0,
            p50_ms=1000.0,
            p95_ms=1000.0,
            p99_ms=1000.0,
            error_rate=0.0,
            generation_throughput_tps=2.0,
            request_throughput_rps=1.0,
        ),
    )
