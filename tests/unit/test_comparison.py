"""Comparison and phase label on constructed experiments.

Clock values and aggregate numbers are fixtures. No test asserts a live
latency. No test reads a findings file for an expected timing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import fields, replace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.benchmark.records import BenchmarkRun, Phase, RequestRecord
from app.database.models import Base
from app.database.repository import StoredExperiment, load_experiments, save_experiment
from app.metrics.statistics import AggregateSummary
from app.monitoring.sampler import ResourceSample
from app.monitoring.snapshot import ConfigurationSnapshot
from app.optimization.comparison import Comparison, SettingDifference, compare
from app.optimization.experiments import phase_label


def _summary(**overrides: float | None) -> AggregateSummary:
    values: dict[str, float | None] = {
        "average_ms": None,
        "median_ms": None,
        "p50_ms": None,
        "p95_ms": None,
        "p99_ms": None,
        "error_rate": None,
        "generation_throughput_tps": None,
        "request_throughput_rps": None,
    }
    values.update(overrides)
    return AggregateSummary(**values)


def _snapshot(**overrides: object) -> ConfigurationSnapshot:
    snapshot = ConfigurationSnapshot(
        model="gemma3:1b",
        prompt="Hi",
        num_predict=32,
        warmup_count=2,
        measured_count=3,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.test",
        capture_time=1.0,
        cpu_model="fixture-cpu",
        logical_cpu_count=12,
        total_ram_bytes=1000,
        python_version="3.13.5",
        profile_name="short_prompt_short_output",
    )
    return replace(snapshot, **overrides)


def _row(
    *,
    phase: Phase = "measured",
    start: float = 0.0,
    first: float | None = 0.8,
    end: float = 1.0,
    success: bool = True,
    error_type: str | None = None,
    end_to_end_ms: float = 1000.0,
    eval_duration: int | None = 20,
) -> RequestRecord:
    return RequestRecord(
        phase=phase,
        model="gemma3:1b",
        prompt="Hi",
        num_predict=32,
        client_start=start,
        first_content_at=first,
        client_end=end,
        end_to_end_ms=end_to_end_ms,
        success=success,
        error_type=error_type,
        eval_count=4,
        prompt_eval_count=2,
        prompt_eval_duration=10,
        eval_duration=eval_duration,
    )


def _stored(
    experiment_id: int,
    *,
    snapshot: ConfigurationSnapshot | None = None,
    measured: tuple[RequestRecord, ...] = (),
    warmup: tuple[RequestRecord, ...] = (),
    samples: tuple[ResourceSample, ...] = (),
    summary: AggregateSummary | None = None,
) -> StoredExperiment:
    return StoredExperiment(
        experiment_id=experiment_id,
        snapshot=snapshot if snapshot is not None else _snapshot(),
        warmup=warmup,
        measured=measured,
        resource_samples=samples,
        sampling_error=None,
        summary=summary if summary is not None else _summary(),
    )


def _engine():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    engine = create_engine(
        "sqlite:///:memory:",
        creator=lambda: connection,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_deltas_are_candidate_minus_baseline() -> None:
    baseline = _stored(
        1,
        summary=_summary(
            average_ms=100.0,
            median_ms=90.0,
            p50_ms=80.0,
            p95_ms=200.0,
            p99_ms=None,
            error_rate=0.0,
            generation_throughput_tps=1.0,
            request_throughput_rps=0.4,
        ),
    )
    candidate = _stored(
        2,
        summary=_summary(
            average_ms=140.0,
            median_ms=100.0,
            p50_ms=90.0,
            p95_ms=500.0,
            p99_ms=800.0,
            error_rate=0.25,
            generation_throughput_tps=2.5,
            request_throughput_rps=0.9,
        ),
    )

    result = compare(baseline, candidate)

    assert result.baseline_experiment_id == 1
    assert result.candidate_experiment_id == 2
    assert result.average_ms_delta == 40.0
    assert result.median_ms_delta == 10.0
    assert result.p50_ms_delta == 10.0
    assert result.p95_ms_delta == 300.0
    assert result.p99_ms_delta is None
    assert result.error_rate_delta == 0.25
    assert result.generation_throughput_tps_delta == 1.5
    assert result.request_throughput_rps_delta == 0.5


def test_setting_differences_keep_null_and_skip_matches() -> None:
    baseline = _stored(1, snapshot=_snapshot(think=None, num_thread=None, concurrency=1))
    candidate = _stored(2, snapshot=_snapshot(think=False, num_thread=4, concurrency=1))

    result = compare(baseline, candidate)

    assert result.setting_differences == (
        SettingDifference(field="think", baseline=None, candidate=False),
        SettingDifference(field="num_thread", baseline=None, candidate=4),
    )
    assert all(item.field != "concurrency" for item in result.setting_differences)
    assert result.setting_differences[1].baseline is None


def test_phase_fixtures_return_prefill_decode_and_even() -> None:
    prefill = _stored(1, measured=(_row(start=0.0, first=0.8, end=1.0, eval_duration=5_000_000_000),))
    decode = _stored(2, measured=(_row(start=0.0, first=0.2, end=1.0),))
    even = _stored(3, measured=(_row(start=0.0, first=0.5, end=1.0),))

    assert phase_label(prefill) == "prefill"
    assert phase_label(decode) == "decode"
    assert phase_label(even) == "even"
    assert compare(prefill, decode).baseline_phase_label == "prefill"
    assert compare(prefill, decode).candidate_phase_label == "decode"


def test_warmup_and_failed_rows_stay_out_of_the_phase_sums() -> None:
    experiment = _stored(
        1,
        warmup=(_row(phase="warmup", start=0.0, first=0.9, end=1.0),),
        measured=(
            _row(
                start=0.0,
                first=0.95,
                end=1.0,
                success=False,
                error_type="OllamaTimeoutError",
            ),
            _row(
                start=0.0,
                first=0.99,
                end=1.0,
                success=False,
                error_type="CancelledError",
            ),
            _row(start=0.0, first=0.2, end=1.0),
        ),
    )

    assert phase_label(experiment) == "decode"


def test_phase_label_is_unset_when_the_share_is_missing_or_zero() -> None:
    failed_only = _stored(
        1,
        measured=(_row(success=False, error_type="OllamaTimeoutError", first=0.1),),
    )
    both_zero = _stored(2, measured=(_row(start=0.0, first=0.0, end=0.0),))

    assert phase_label(failed_only) is None
    assert phase_label(both_zero) is None


def test_stored_average_is_not_recomputed_from_the_rows() -> None:
    baseline = _stored(
        1,
        summary=_summary(average_ms=10.0),
        measured=(_row(end_to_end_ms=1000.0),),
    )
    candidate = _stored(
        2,
        summary=_summary(average_ms=40.0),
        measured=(_row(end_to_end_ms=5.0),),
    )

    result = compare(baseline, candidate)

    assert result.average_ms_delta == 30.0
    assert baseline.measured[0].end_to_end_ms == 1000.0
    assert candidate.measured[0].end_to_end_ms == 5.0


def test_cpu_sample_range_is_not_a_latency_delta() -> None:
    samples = (
        ResourceSample(
            taken_at=1.0,
            cpu_percent=0.0,
            system_ram_used_bytes=10,
            system_ram_total_bytes=20,
            process_rss_bytes=5,
        ),
        ResourceSample(
            taken_at=2.0,
            cpu_percent=70.0,
            system_ram_used_bytes=50,
            system_ram_total_bytes=20,
            process_rss_bytes=5,
        ),
    )
    baseline = _stored(
        1,
        samples=samples,
        summary=_summary(average_ms=100.0, p95_ms=200.0),
    )
    candidate = _stored(
        2,
        samples=(),
        summary=_summary(average_ms=140.0, p95_ms=500.0),
    )

    result = compare(baseline, candidate)

    assert result.baseline_samples.sample_count == 2
    assert result.baseline_samples.cpu_percent_min == 0.0
    assert result.baseline_samples.cpu_percent_max == 70.0
    assert result.candidate_samples.sample_count == 0
    assert result.candidate_samples.cpu_percent_min is None
    assert result.candidate_samples.cpu_percent_max is None
    assert result.candidate_samples.system_ram_used_bytes_min is None
    assert result.candidate_samples.system_ram_used_bytes_max is None
    assert result.average_ms_delta == 40.0
    assert result.p95_ms_delta == 300.0
    assert result.average_ms_delta not in (0.0, 70.0)
    assert result.p95_ms_delta not in (0.0, 70.0)


def test_sign_sentence_names_both_signs_and_does_not_rank() -> None:
    baseline = _stored(1, summary=_summary(p95_ms=200.0, request_throughput_rps=0.4))
    candidate = _stored(2, summary=_summary(p95_ms=500.0, request_throughput_rps=0.9))

    result = compare(baseline, candidate)

    assert result.sign_sentence == "Request throughput is higher and P95 is higher."
    assert result.sign_sentence is not None
    for word in ("better", "worse", "improved", "winner"):
        assert word not in result.sign_sentence

    lower = compare(
        _stored(3, summary=_summary(p95_ms=500.0, request_throughput_rps=0.9)),
        _stored(4, summary=_summary(p95_ms=200.0, request_throughput_rps=0.4)),
    )
    assert lower.sign_sentence == "Request throughput is lower and P95 is lower."

    unset = compare(
        _stored(5, summary=_summary(p95_ms=200.0, request_throughput_rps=0.4)),
        _stored(6, summary=_summary(p95_ms=None, request_throughput_rps=0.9)),
    )
    assert unset.sign_sentence is None


def test_result_type_has_no_winner_field() -> None:
    result = compare(_stored(1), _stored(2))
    names = {item.name for item in fields(Comparison)}
    names.update(field.name for field in fields(result))

    assert "winner" not in names
    assert "improved" not in names
    assert "recommendation" not in names


def test_omitted_num_thread_loads_in_the_difference_list_as_null() -> None:
    engine = _engine()
    baseline_summary = _summary(average_ms=10.0)
    candidate_summary = _summary(average_ms=40.0)
    with Session(engine) as session:
        save_experiment(
            session,
            BenchmarkRun(
                warmup=(),
                measured=(_row(end_to_end_ms=1000.0),),
                concurrency=1,
            ),
            _snapshot(num_thread=None),
            baseline_summary,
        )
        save_experiment(
            session,
            BenchmarkRun(
                warmup=(),
                measured=(_row(end_to_end_ms=5.0),),
                concurrency=1,
            ),
            _snapshot(num_thread=4),
            candidate_summary,
        )
        session.commit()
    with Session(engine) as session:
        loaded = load_experiments(session)

    result = compare(loaded[0], loaded[1])

    assert [item.experiment_id for item in loaded] == [1, 2]
    assert loaded[0].summary.average_ms == 10.0
    assert loaded[0].measured[0].end_to_end_ms == 1000.0
    assert loaded[1].snapshot.num_thread == 4
    assert result.average_ms_delta == 30.0
    assert result.setting_differences == (
        SettingDifference(field="num_thread", baseline=None, candidate=4),
    )
    assert result.setting_differences[0].baseline is None
