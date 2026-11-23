"""In-memory save and load. The connection is shared.

Ollama is not contacted. Clock values, durations, and resource numbers are
fixtures. No test asserts a live CPU percent or a latency number from a live
server.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.benchmark.records import BenchmarkRun, RequestRecord
from app.database.models import Base
from app.database.repository import load_experiment, load_experiments, save_experiment
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
    assert loaded.snapshot.profile_name is None
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


def test_missing_profile_name_loads_back_as_null() -> None:
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot())
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert _run().profile_name is None
    assert loaded.snapshot.profile_name is None


def test_snapshot_profile_name_loads_back() -> None:
    snapshot = replace(_snapshot(), profile_name="long_prompt_short_output")
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), snapshot)
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert loaded.snapshot.profile_name == "long_prompt_short_output"


def test_omitted_think_flag_loads_back_as_null() -> None:
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot())
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert _snapshot().think is None
    assert loaded.snapshot.think is None
    assert loaded.snapshot.quantization is None
    assert loaded.snapshot.parameter_size is None
    assert loaded.snapshot.model_size_bytes is None
    assert loaded.snapshot.architecture is None


def test_think_false_and_model_metadata_load_back() -> None:
    snapshot = replace(
        _snapshot(),
        think=False,
        quantization="Q8_0",
        parameter_size="1.9B",
        model_size_bytes=2683396812,
        architecture="qwen35",
    )
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), snapshot)
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert loaded.snapshot.think is False
    assert loaded.snapshot.quantization == "Q8_0"
    assert loaded.snapshot.parameter_size == "1.9B"
    assert loaded.snapshot.model_size_bytes == 2683396812
    assert loaded.snapshot.architecture == "qwen35"


def test_omitted_num_thread_loads_back_as_null() -> None:
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot())
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert _snapshot().num_thread is None
    assert loaded.snapshot.num_thread is None


def test_load_experiments_returns_id_order_and_keeps_the_stored_average() -> None:
    slow = RequestRecord(
        phase="measured",
        model="gemma3:1b",
        prompt="Hi",
        num_predict=8,
        client_start=0.0,
        first_content_at=0.2,
        client_end=1.0,
        end_to_end_ms=1000.0,
        success=True,
        error_type=None,
        eval_count=4,
        prompt_eval_count=2,
        prompt_eval_duration=10,
        eval_duration=20,
    )
    stored = AggregateSummary(
        average_ms=10.0,
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
        first = save_experiment(session, _run(), _snapshot(), stored)
        second = save_experiment(
            session,
            BenchmarkRun(warmup=(), measured=(slow,), concurrency=1),
            replace(_snapshot(), model="qwen3.5:2b"),
            replace(stored, average_ms=40.0),
        )
        session.commit()
    with Session(engine) as session:
        loaded = load_experiments(session)

    assert [item.experiment_id for item in loaded] == [first, second]
    assert first < second
    assert loaded[0].summary.average_ms == 10.0
    assert loaded[0].summary.p95_ms is None
    assert loaded[1].summary.average_ms == 40.0
    assert loaded[1].measured[0].end_to_end_ms == 1000.0
    assert loaded[1].snapshot.model == "qwen3.5:2b"


def test_missing_stored_columns_load_as_null() -> None:
    engine = _legacy_engine(
        _legacy_experiments(think_column=False)
        + _LEGACY_CHILD_TABLES
        + _LEGACY_ROW
    )
    with Session(engine) as session:
        loaded = load_experiments(session)

    assert loaded[0].snapshot.think is None
    assert loaded[0].snapshot.num_thread is None
    assert loaded[0].snapshot.quantization is None
    assert loaded[0].snapshot.parameter_size is None
    assert loaded[0].snapshot.model_size_bytes is None
    assert loaded[0].snapshot.architecture is None
    assert loaded[0].snapshot.routing_policy is None
    assert loaded[0].snapshot.preferred_model is None
    assert loaded[0].snapshot.fallback_count is None
    assert loaded[0].snapshot.retry_count is None
    assert loaded[0].summary.average_ms == 10.0
    with engine.connect() as connection:
        info = connection.exec_driver_sql("PRAGMA table_info(experiments)").all()
    column_names = {row[1] for row in info}
    assert "routing_policy" not in column_names
    assert "preferred_model" not in column_names
    assert "fallback_count" not in column_names
    assert "retry_count" not in column_names
    assert loaded[0].measured[0].end_to_end_ms == 1000.0


def test_stored_think_zero_loads_as_false_when_num_thread_is_absent() -> None:
    engine = _legacy_engine(
        _legacy_experiments(think_column=True)
        + _LEGACY_CHILD_TABLES
        + """
        INSERT INTO experiments (
            id, model, prompt, num_predict, warmup_count, measured_count, concurrency,
            engine_name, engine_version, capture_time, cpu_model, logical_cpu_count,
            total_ram_bytes, python_version, profile_name, think, average_ms
        ) VALUES (
            1, 'gemma3:1b', 'Hi', 32, 2, 3, 1,
            'ollama', '0.test', 1.0, 'fixture-cpu', 12,
            1000, '3.13.5', 'short_prompt_short_output', 0, 10.0
        );
        INSERT INTO request_rows (
            id, experiment_id, ordinal, phase, model, prompt, num_predict,
            client_start, first_content_at, client_end, end_to_end_ms, success,
            error_type, eval_count, prompt_eval_count, prompt_eval_duration, eval_duration
        ) VALUES (
            1, 1, 0, 'measured', 'gemma3:1b', 'Hi', 32,
            0.0, 0.2, 1.0, 1000.0, 1,
            NULL, 4, 2, 10, 20
        );
        """
    )
    with Session(engine) as session:
        loaded = load_experiments(session)

    assert loaded[0].snapshot.think is False
    assert loaded[0].snapshot.num_thread is None


def _legacy_engine(script: str):
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(script)
    return create_engine(
        "sqlite:///:memory:",
        creator=lambda: connection,
        poolclass=StaticPool,
    )


def _legacy_experiments(*, think_column: bool) -> str:
    think = "think BOOLEAN," if think_column else ""
    return f"""
    CREATE TABLE experiments (
        id INTEGER PRIMARY KEY,
        sampling_error VARCHAR,
        model VARCHAR NOT NULL,
        prompt VARCHAR NOT NULL,
        num_predict INTEGER,
        warmup_count INTEGER NOT NULL,
        measured_count INTEGER NOT NULL,
        concurrency INTEGER NOT NULL,
        engine_name VARCHAR NOT NULL,
        engine_version VARCHAR NOT NULL,
        capture_time FLOAT NOT NULL,
        cpu_model VARCHAR NOT NULL,
        logical_cpu_count INTEGER NOT NULL,
        total_ram_bytes INTEGER NOT NULL,
        python_version VARCHAR NOT NULL,
        profile_name VARCHAR,
        {think}
        average_ms FLOAT,
        median_ms FLOAT,
        p50_ms FLOAT,
        p95_ms FLOAT,
        p99_ms FLOAT,
        error_rate FLOAT,
        generation_throughput_tps FLOAT,
        request_throughput_rps FLOAT
    );
    """


_LEGACY_CHILD_TABLES = """
CREATE TABLE request_rows (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    phase VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    prompt VARCHAR NOT NULL,
    num_predict INTEGER,
    client_start FLOAT NOT NULL,
    first_content_at FLOAT,
    client_end FLOAT NOT NULL,
    end_to_end_ms FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    error_type VARCHAR,
    eval_count INTEGER,
    prompt_eval_count INTEGER,
    prompt_eval_duration INTEGER,
    eval_duration INTEGER
);
CREATE TABLE resource_samples (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    taken_at FLOAT NOT NULL,
    cpu_percent FLOAT NOT NULL,
    system_ram_used_bytes INTEGER NOT NULL,
    system_ram_total_bytes INTEGER NOT NULL,
    process_rss_bytes INTEGER NOT NULL
);
"""

_LEGACY_ROW = """
INSERT INTO experiments (
    id, model, prompt, num_predict, warmup_count, measured_count, concurrency,
    engine_name, engine_version, capture_time, cpu_model, logical_cpu_count,
    total_ram_bytes, python_version, profile_name, average_ms
) VALUES (
    1, 'gemma3:1b', 'Hi', 32, 2, 3, 1,
    'ollama', '0.test', 1.0, 'fixture-cpu', 12,
    1000, '3.13.5', 'short_prompt_short_output', 10.0
);
INSERT INTO request_rows (
    id, experiment_id, ordinal, phase, model, prompt, num_predict,
    client_start, first_content_at, client_end, end_to_end_ms, success,
    error_type, eval_count, prompt_eval_count, prompt_eval_duration, eval_duration
) VALUES (
    1, 1, 0, 'measured', 'gemma3:1b', 'Hi', 32,
    0.0, 0.2, 1.0, 1000.0, 1,
    NULL, 4, 2, 10, 20
);
"""


def test_stored_num_thread_4_loads_back_as_4() -> None:
    snapshot = replace(_snapshot(), num_thread=4)
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), snapshot)
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)

    assert loaded.snapshot.num_thread == 4


def test_omitted_routing_policy_loads_back_as_null() -> None:
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), _snapshot())
        session.commit()
    with Session(engine) as session:
        loaded = load_experiments(session)

    assert loaded[0].experiment_id == experiment_id
    assert loaded[0].snapshot.routing_policy is None
    assert loaded[0].snapshot.preferred_model is None
    assert loaded[0].snapshot.fallback_count is None
    assert loaded[0].snapshot.retry_count is None


def test_stored_fallback_count_1_and_retry_count_0_load_back() -> None:
    snapshot = replace(
        _snapshot(),
        routing_policy="availability_aware",
        preferred_model="qwen3.5:2b",
        fallback_count=1,
        retry_count=0,
    )
    engine = _engine()
    with Session(engine) as session:
        experiment_id = save_experiment(session, _run(), snapshot)
        session.commit()
    with Session(engine) as session:
        loaded = load_experiment(session, experiment_id)
        listed = load_experiments(session)

    assert loaded.snapshot.routing_policy == "availability_aware"
    assert loaded.snapshot.preferred_model == "qwen3.5:2b"
    assert loaded.snapshot.fallback_count == 1
    assert loaded.snapshot.retry_count == 0
    assert listed[0].snapshot.fallback_count == 1
    assert listed[0].snapshot.retry_count == 0
