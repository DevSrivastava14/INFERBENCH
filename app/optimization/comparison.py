"""Compare two stored experiments.

A delta is the candidate's stored aggregate minus the baseline's stored
aggregate. This module reads ``AggregateSummary`` on the stored experiment.
It does not call ``summarize``. It does not call Ollama, does not call
``psutil``, and does not open SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.database.repository import StoredExperiment
from app.monitoring.sampler import ResourceSample
from app.optimization.experiments import PhaseLabel, phase_label

_DELTA_FIELDS = (
    "average_ms",
    "median_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "error_rate",
    "generation_throughput_tps",
    "request_throughput_rps",
)

_SETTING_FIELDS = (
    "model",
    "profile_name",
    "prompt",
    "num_predict",
    "warmup_count",
    "measured_count",
    "concurrency",
    "think",
    "num_thread",
    "quantization",
    "parameter_size",
    "model_size_bytes",
    "architecture",
    "engine_name",
    "engine_version",
    "cpu_model",
    "logical_cpu_count",
    "total_ram_bytes",
    "python_version",
)


@dataclass(frozen=True)
class SettingDifference:
    """One snapshot field whose stored values differ.

    ``baseline`` and ``candidate`` are the stored values. Null stays null.
    """

    field: str
    baseline: str | int | bool | None
    candidate: str | int | bool | None


@dataclass(frozen=True)
class SampleRange:
    """Stored sample count and the min and max of two sample fields.

    An empty sample list leaves the four numbers unset. A sample of 0 stays
    in the min. These numbers are not latency deltas.
    """

    sample_count: int
    cpu_percent_min: float | None
    cpu_percent_max: float | None
    system_ram_used_bytes_min: int | None
    system_ram_used_bytes_max: int | None


@dataclass(frozen=True)
class Comparison:
    """Deltas, phase labels, setting differences, and sample ranges.

    Each ``*_delta`` is the candidate's stored aggregate minus the baseline's
    stored aggregate. An unset side leaves that delta unset. This object has
    no winner, improved, or recommendation field.
    """

    baseline_experiment_id: int
    candidate_experiment_id: int
    average_ms_delta: float | None
    median_ms_delta: float | None
    p50_ms_delta: float | None
    p95_ms_delta: float | None
    p99_ms_delta: float | None
    error_rate_delta: float | None
    generation_throughput_tps_delta: float | None
    request_throughput_rps_delta: float | None
    baseline_phase_label: PhaseLabel | None
    candidate_phase_label: PhaseLabel | None
    setting_differences: tuple[SettingDifference, ...]
    baseline_samples: SampleRange
    candidate_samples: SampleRange
    sign_sentence: str | None


def compare(baseline: StoredExperiment, candidate: StoredExperiment) -> Comparison:
    """Return one frozen comparison of two stored experiments.

    The caller supplies both experiments. There is no built-in anchor.
    Deltas read the stored ``AggregateSummary`` and do not call ``summarize``.
    Setting differences follow the snapshot field order. Matching fields stay
    off the list. The sign sentence is present only when the request-throughput
    delta and the P95 delta are both defined and both non-zero.
    """

    deltas = {
        name: _delta(getattr(baseline.summary, name), getattr(candidate.summary, name))
        for name in _DELTA_FIELDS
    }
    return Comparison(
        baseline_experiment_id=baseline.experiment_id,
        candidate_experiment_id=candidate.experiment_id,
        average_ms_delta=deltas["average_ms"],
        median_ms_delta=deltas["median_ms"],
        p50_ms_delta=deltas["p50_ms"],
        p95_ms_delta=deltas["p95_ms"],
        p99_ms_delta=deltas["p99_ms"],
        error_rate_delta=deltas["error_rate"],
        generation_throughput_tps_delta=deltas["generation_throughput_tps"],
        request_throughput_rps_delta=deltas["request_throughput_rps"],
        baseline_phase_label=phase_label(baseline),
        candidate_phase_label=phase_label(candidate),
        setting_differences=_setting_differences(baseline, candidate),
        baseline_samples=_sample_range(baseline.resource_samples),
        candidate_samples=_sample_range(candidate.resource_samples),
        sign_sentence=_sign_sentence(deltas["request_throughput_rps"], deltas["p95_ms"]),
    )


def _delta(baseline: float | None, candidate: float | None) -> float | None:
    if baseline is None or candidate is None:
        return None
    return candidate - baseline


def _setting_differences(
    baseline: StoredExperiment,
    candidate: StoredExperiment,
) -> tuple[SettingDifference, ...]:
    differences: list[SettingDifference] = []
    for field in _SETTING_FIELDS:
        baseline_value = getattr(baseline.snapshot, field)
        candidate_value = getattr(candidate.snapshot, field)
        if baseline_value != candidate_value:
            differences.append(
                SettingDifference(
                    field=field,
                    baseline=baseline_value,
                    candidate=candidate_value,
                )
            )
    return tuple(differences)


def _sample_range(samples: tuple[ResourceSample, ...]) -> SampleRange:
    if not samples:
        return SampleRange(
            sample_count=0,
            cpu_percent_min=None,
            cpu_percent_max=None,
            system_ram_used_bytes_min=None,
            system_ram_used_bytes_max=None,
        )
    cpu_values = tuple(sample.cpu_percent for sample in samples)
    ram_values = tuple(sample.system_ram_used_bytes for sample in samples)
    return SampleRange(
        sample_count=len(samples),
        cpu_percent_min=min(cpu_values),
        cpu_percent_max=max(cpu_values),
        system_ram_used_bytes_min=min(ram_values),
        system_ram_used_bytes_max=max(ram_values),
    )


def _sign_sentence(request_delta: float | None, p95_delta: float | None) -> str | None:
    if request_delta is None or p95_delta is None:
        return None
    if request_delta == 0 or p95_delta == 0:
        return None
    request_word = "higher" if request_delta > 0 else "lower"
    p95_word = "higher" if p95_delta > 0 else "lower"
    return f"Request throughput is {request_word} and P95 is {p95_word}."
