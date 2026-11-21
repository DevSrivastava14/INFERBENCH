"""In-memory save and load. The connection is shared.

Ollama is not contacted. Clock values, durations, and resource numbers are
fixtures. No test asserts a live CPU percent or a latency number from a live
server.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.benchmark.records import BenchmarkRun, RequestRecord
from app.database.models import Base
from app.database.repository import load_experiment, save_experiment
from app.metrics.statistics import AggregateSummary
from app.monitoring.sampler import ResourceSample
from app.monitoring.snapshot import ConfigurationSnapshot


def _engine():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    engine = create_engine(
        "sqlite:///:memory:",
        creator=lambda: connection,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _warmup() -> RequestRecord:
    return RequestRecord(
        phase="warmup",
        model="gemma3:1b",
        prompt="Hi",
        num_predict=8,
        client_start=1.0,
        first_content_at=1.2,
        client_end=1.5,
        end_to_end_ms=500.0,
        success=True,
        error_type=None,
        eval_count=4,
        prompt_eval_count=2,
        prompt_eval_duration=10,
        eval_duration=20,
    )


def _measured() -> RequestRecord:
    return RequestRecord(
        phase="measured",
        model="gemma3:1b",
        prompt="Hi",
        num_predict=8,
        client_start=2.0,
        first_content_at=None,
        client_end=2.4,
        end_to_end_ms=400.0,
        success=False,
        error_type="OllamaTimeoutError",
        eval_count=None,
        prompt_eval_count=None,
        prompt_eval_duration=None,
        eval_duration=None,
    )


def _sample() -> ResourceSample:
    return ResourceSample(
        taken_at=3.0,
        cpu_percent=0.0,
        system_ram_used_bytes=11,
        system_ram_total_bytes=22,
        process_rss_bytes=33,
    )


def _snapshot() -> ConfigurationSnapshot:
    return ConfigurationSnapshot(
        model="gemma3:1b",
        prompt="Hi",
        num_predict=8,
        warmup_count=1,
        measured_count=1,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.test",
        capture_time=9.0,
        cpu_model="fixture-cpu",
        logical_cpu_count=8,
        total_ram_bytes=99,
        python_version="3.x",
    )


def _run() -> BenchmarkRun:
    return BenchmarkRun(
        warmup=(_warmup(),),
        measured=(_measured(),),
        concurrency=1,
        resource_samples=(_sample(),),
        sampling_error=None,
    )


def test_save_and_load_round_trips_rows_sample_and_null_p95() -> None:
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot())
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert loaded.snapshot == _snapshot()
    assert loaded.warmup == (_warmup(),)
    assert loaded.measured == (_measured(),)
    assert loaded.resource_samples == (_sample(),)
    assert loaded.summary.p95_ms is None
    assert loaded.summary.average_ms is None
    assert loaded.summary.generation_throughput_tps is None
    assert loaded.summary.request_throughput_rps is None


def test_stored_summary_reloads_the_same_average_and_null_fields() -> None:
    summary = AggregateSummary(
        average_ms=12.5,
        median_ms=None,
        p50_ms=None,
        p95_ms=None,
        p99_ms=None,
        error_rate=None,
        generation_throughput_tps=None,
        request_throughput_rps=None,
    )
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot(), summary)
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert loaded.summary == summary
    assert loaded.summary.average_ms == 12.5
    assert loaded.summary.p95_ms is None
