"""API tests. The adapter is a fake. The database is temporary.

Ollama is not contacted. No test asserts a latency number from a live server.
The four stored result files are not opened.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.benchmark.records import BenchmarkRun
from app.core.exceptions import ModelNotInstalledError, OllamaTimeoutError, OllamaUnavailableError
from app.database.models import Base
from app.database.repository import load_experiment, save_experiment
from app.inference.base import (
    GenerateOptions,
    GenerateResult,
    InferenceAdapter,
    ModelInfo,
    StreamGenerateResult,
)
from app.main import create_app
from app.metrics.statistics import AggregateSummary, summarize
from app.monitoring.sampler import ResourceReading
from app.monitoring.snapshot import ConfigurationSnapshot, HardwareIdentity

FORBIDDEN = ("winner", "improved", "recommendation", "best")


class FakeAdapter(InferenceAdapter):
    """In-memory adapter. It never opens a socket."""

    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.started = asyncio.Event()
        self.hold = False
        self.stream_calls = 0
        self.thinks: list[bool | None] = []
        self.version_error: Exception | None = None
        self.show_error: Exception | None = None
        self.stream_error: Exception | None = None
        self.fail_after = 0

    async def engine_version(self) -> str:
        if self.version_error is not None:
            raise self.version_error
        return "0.test"

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                name="gemma3:1b",
                size=1,
                quantization=None,
                parameter_size=None,
                raw={},
            )
        ]

    async def show_model(self, name: str) -> ModelInfo:
        if self.show_error is not None:
            raise self.show_error
        return ModelInfo(name=name, size=None, quantization=None, parameter_size=None, raw={})

    async def generate(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
    ) -> GenerateResult:
        raise AssertionError("the API task must not call non-streaming generate")

    async def generate_stream(
        self,
        model: str,
        prompt: str,
        options: GenerateOptions | None = None,
        *,
        clock,
    ) -> StreamGenerateResult:
        self.stream_calls += 1
        self.thinks.append(None if options is None else options.think)
        self.started.set()
        if self.hold:
            await self.release.wait()
        if self.stream_error is not None and self.stream_calls > self.fail_after:
            raise self.stream_error
        return StreamGenerateResult(
            text="ok",
            metadata={
                "eval_count": 2,
                "prompt_eval_count": 1,
                "prompt_eval_duration": 1,
                "eval_duration": 1,
            },
            chunk_count=1,
            first_content_at=clock(),
        )


def _hardware() -> HardwareIdentity:
    return HardwareIdentity(
        cpu_model="fixture-cpu",
        logical_cpu_count=4,
        total_ram_bytes=8,
        python_version="3.x",
    )


def _resource() -> ResourceReading:
    return ResourceReading(
        cpu_percent=0.0,
        system_ram_used_bytes=3,
        system_ram_total_bytes=8,
        process_rss_bytes=1,
    )


def _build(tmp_path: Path, adapter: FakeAdapter, **kwargs):
    dashboard = tmp_path / "dashboard.sqlite"
    app = create_app(
        adapter=adapter,
        dashboard_path=dashboard,
        result_paths=kwargs.get("result_paths", {}),
        hardware_probe=kwargs.get("hardware_probe", _hardware),
        resource_probe=kwargs.get("resource_probe", _resource),
        clock=lambda: 1.0,
    )
    return app, dashboard


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _wait_status(client: AsyncClient, job_id: int, status: str) -> dict:
    last = {}
    for _ in range(100):
        response = await client.get(f"/api/jobs/{job_id}")
        last = response.json()
        if last["job_status"] == status:
            return last
        await asyncio.sleep(0.01)
    pytest.fail(f"job {job_id} stayed {last.get('job_status')!r}, expected {status}")


def _assert_no_forbidden(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert key not in FORBIDDEN
            _assert_no_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_forbidden(item)


@pytest.mark.asyncio
async def test_blocked_run_is_running_then_completed_with_aggregates(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.hold = True
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        posted = await client.post("/api/jobs", json={"model": "gemma3:1b", "prompt": "Hi"})
        assert posted.status_code == 200
        body = posted.json()
        assert body["job_status"] == "PENDING"
        job_id = body["id"]
        await asyncio.wait_for(adapter.started.wait(), timeout=2)
        running = await client.get(f"/api/jobs/{job_id}")
        assert running.json()["job_status"] == "RUNNING"
        assert running.json()["warmup_count"] == 2
        assert running.json()["measured_count"] == 3
        assert running.json()["succeeded_count"] == 0
        adapter.release.set()
        completed = await _wait_status(client, job_id, "COMPLETED")

    assert completed["succeeded_count"] == 5
    assert completed["failed_count"] == 0
    assert adapter.thinks == [None, None, None, None, None]
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, job_id)
        columns = session.connection().exec_driver_sql("PRAGMA table_info(request_rows)").all()
    engine.dispose()
    assert loaded.job_status == "COMPLETED"
    assert loaded.summary == summarize(
        BenchmarkRun(
            warmup=loaded.warmup,
            measured=loaded.measured,
            concurrency=loaded.snapshot.concurrency,
        )
    )
    assert loaded.summary.average_ms is not None
    assert loaded.snapshot.retry_count == 0
    assert "job_status" not in {row[1] for row in columns}


@pytest.mark.asyncio
async def test_cancel_ends_cancelled(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.hold = True
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        posted = await client.post(
            "/api/jobs",
            json={
                "model": "gemma3:1b",
                "prompt": "Hi",
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        job_id = posted.json()["id"]
        await asyncio.wait_for(adapter.started.wait(), timeout=2)
        running = await client.get(f"/api/jobs/{job_id}")
        assert running.json()["job_status"] == "RUNNING"
        cancelled = await client.post(f"/api/jobs/{job_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["job_status"] == "RUNNING"
        finished = await _wait_status(client, job_id, "CANCELLED")

    assert finished["job_status"] == "CANCELLED"
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, job_id)
    engine.dispose()
    assert loaded.job_status == "CANCELLED"
    assert loaded.summary.average_ms is None
    assert [row.error_type for row in loaded.measured] == ["CancelledError"]
    assert loaded.snapshot.retry_count == 0


@pytest.mark.asyncio
async def test_think_true_creates_no_job(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        response = await client.post(
            "/api/jobs",
            json={"model": "qwen3.5:2b", "prompt": "Hi", "think": True},
        )

    assert response.status_code == 422
    assert adapter.stream_calls == 0
    assert dashboard.exists() is False


@pytest.mark.asyncio
async def test_empty_model_empty_prompt_and_low_concurrency_create_no_job(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    app, dashboard = _build(tmp_path, adapter)
    bodies = (
        {"model": "  ", "prompt": "Hi"},
        {"model": "gemma3:1b", "prompt": ""},
        {"model": "gemma3:1b", "prompt": "Hi", "concurrency": 0},
    )
    async with _client(app) as client:
        for body in bodies:
            response = await client.post("/api/jobs", json=body)
            assert response.status_code == 422

    assert adapter.stream_calls == 0
    assert dashboard.exists() is False


@pytest.mark.asyncio
async def test_qwen_sends_think_false_and_gemma_omits_it(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        qwen = await client.post(
            "/api/jobs",
            json={
                "model": "qwen3.5:2b",
                "prompt": "Hi",
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        await _wait_status(client, qwen.json()["id"], "COMPLETED")
        gemma = await client.post(
            "/api/jobs",
            json={
                "model": "gemma3:1b",
                "prompt": "Hi",
                "think": False,
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        await _wait_status(client, gemma.json()["id"], "COMPLETED")
        other_omitted = await client.post(
            "/api/jobs",
            json={
                "model": "other:1b",
                "prompt": "Hi",
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        await _wait_status(client, other_omitted.json()["id"], "COMPLETED")
        other_false = await client.post(
            "/api/jobs",
            json={
                "model": "other:1b",
                "prompt": "Hi",
                "think": False,
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        await _wait_status(client, other_false.json()["id"], "COMPLETED")

    assert adapter.thinks == [False, None, None, False]
    assert dashboard.exists() is True


@pytest.mark.asyncio
async def test_request_error_still_completes(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.stream_error = OllamaTimeoutError("timed out")
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        posted = await client.post(
            "/api/jobs",
            json={
                "model": "gemma3:1b",
                "prompt": "Hi",
                "warmup_count": 0,
                "measured_count": 1,
            },
        )
        finished = await _wait_status(client, posted.json()["id"], "COMPLETED")

    assert finished["failed_count"] == 1
    assert finished["job_status"] == "COMPLETED"
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, posted.json()["id"])
    engine.dispose()
    assert loaded.measured[0].error_type == "OllamaTimeoutError"
    assert loaded.job_status == "COMPLETED"


@pytest.mark.asyncio
async def test_raised_run_stores_sink_rows_and_null_aggregates(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.stream_error = RuntimeError("boom")
    adapter.fail_after = 1
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        posted = await client.post(
            "/api/jobs",
            json={
                "model": "gemma3:1b",
                "prompt": "Hi",
                "warmup_count": 0,
                "measured_count": 2,
            },
        )
        finished = await _wait_status(client, posted.json()["id"], "FAILED")

    assert finished["succeeded_count"] == 1
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, posted.json()["id"])
    engine.dispose()
    assert loaded.job_status == "FAILED"
    assert len(loaded.measured) == 1
    assert loaded.measured[0].success is True
    assert loaded.summary.average_ms is None
    assert loaded.summary.p95_ms is None


@pytest.mark.asyncio
async def test_version_failure_and_missing_model_do_not_stream(tmp_path: Path) -> None:
    version_adapter = FakeAdapter()
    version_adapter.version_error = OllamaUnavailableError("down")
    app, dashboard = _build(tmp_path, version_adapter)
    async with _client(app) as client:
        posted = await client.post(
            "/api/jobs",
            json={"model": "gemma3:1b", "prompt": "Hi", "warmup_count": 0, "measured_count": 1},
        )
        failed = await _wait_status(client, posted.json()["id"], "FAILED")
    assert failed["job_status"] == "FAILED"
    assert version_adapter.stream_calls == 0

    missing_adapter = FakeAdapter()
    missing_adapter.show_error = ModelNotInstalledError("gemma3:1b")
    app, dashboard = _build(tmp_path / "missing", missing_adapter)
    async with _client(app) as client:
        posted = await client.post(
            "/api/jobs",
            json={"model": "gemma3:1b", "prompt": "Hi", "warmup_count": 0, "measured_count": 1},
        )
        failed = await _wait_status(client, posted.json()["id"], "FAILED")
    assert failed["job_status"] == "FAILED"
    assert missing_adapter.stream_calls == 0
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, posted.json()["id"])
    engine.dispose()
    assert loaded.summary.average_ms is None
    assert loaded.measured == ()


def test_missing_job_status_column_loads_null_without_a_byte_change(tmp_path: Path) -> None:
    path = tmp_path / "legacy-no-job-status.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
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
            average_ms FLOAT
        );
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
        INSERT INTO experiments (
            id, model, prompt, num_predict, warmup_count, measured_count, concurrency,
            engine_name, engine_version, capture_time, cpu_model, logical_cpu_count,
            total_ram_bytes, python_version, profile_name, average_ms
        ) VALUES (
            1, 'gemma3:1b', 'Hi', 32, 2, 3, 1,
            'ollama', '0.test', 1.0, 'fixture-cpu', 4,
            8, '3.x', 'short_prompt_short_output', 10.0
        );
        INSERT INTO request_rows (
            id, experiment_id, ordinal, phase, model, prompt, num_predict,
            client_start, first_content_at, client_end, end_to_end_ms, success,
            eval_count, prompt_eval_count, prompt_eval_duration, eval_duration
        ) VALUES (
            1, 1, 0, 'measured', 'gemma3:1b', 'Hi', 32,
            0.0, 0.2, 1.0, 1000.0, 1,
            4, 2, 10, 20
        );
        """
    )
    connection.close()
    before = path.read_bytes()
    location = path.resolve().as_posix()
    engine = create_engine(
        "sqlite://",
        creator=lambda: sqlite3.connect(f"file:{location}?mode=ro", uri=True),
        poolclass=NullPool,
    )
    with Session(engine) as session:
        loaded = load_experiment(session, 1)
    engine.dispose()

    assert loaded.job_status is None
    assert loaded.summary.average_ms == 10.0
    assert path.read_bytes() == before
    assert path.name not in {
        "workload-sensitivity.sqlite",
        "model-comparison.sqlite",
        "serving-config.sqlite",
        "routing-effectiveness.sqlite",
    }


@pytest.mark.asyncio
async def test_compare_and_route_have_no_winner_field(tmp_path: Path) -> None:
    dashboard = tmp_path / "dashboard.sqlite"
    _seed_pair(dashboard)
    adapter = FakeAdapter()
    app, _dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        compared = await client.post(
            "/api/compare",
            json={
                "baseline": {"source": "dashboard", "id": 1},
                "candidate": {"source": "dashboard", "id": 2},
            },
        )
        quiet = await client.post(
            "/api/compare",
            json={
                "baseline": {"source": "dashboard", "id": 1},
                "candidate": {"source": "dashboard", "id": 3},
            },
        )
        routed = await client.post(
            "/api/route",
            json={
                "policy": "static",
                "catalog": [],
                "request": {
                    "profile_name": "short_prompt_short_output",
                    "static_model": "gemma3:1b",
                },
                "unavailable": [],
            },
        )

    assert compared.status_code == 200
    assert "sign_sentence" in compared.json()
    _assert_no_forbidden(compared.json())
    assert quiet.status_code == 200
    assert "sign_sentence" not in quiet.json()
    _assert_no_forbidden(quiet.json())
    assert routed.status_code == 200
    assert routed.json()["selected_model"] == "gemma3:1b"
    assert routed.json()["reason"]
    _assert_no_forbidden(routed.json())
    assert adapter.stream_calls == 0


@pytest.mark.asyncio
async def test_history_skips_a_missing_result_file(tmp_path: Path) -> None:
    missing = tmp_path / "workload-sensitivity.sqlite"
    adapter = FakeAdapter()
    app, _dashboard = _build(
        tmp_path,
        adapter,
        result_paths={"workload-sensitivity": missing},
    )
    async with _client(app) as client:
        response = await client.get("/api/history")

    assert response.status_code == 200
    assert response.json() == []
    assert missing.exists() is False


@pytest.mark.asyncio
async def test_overview_returns_the_probe_sample(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    app, _dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        response = await client.get("/api/overview")

    body = response.json()
    assert body["inference_engines"] == [{"name": "ollama", "version": "0.test"}]
    assert body["models"] == [
        {
            "name": "gemma3:1b",
            "size": 1,
            "quantization": None,
            "parameter_size": None,
            "architecture": None,
        }
    ]
    assert body["hardware"]["cpu_model"] == "fixture-cpu"
    assert body["sample"]["cpu_percent"] == 0.0
    assert body["recent_experiments"] == []
    _assert_no_forbidden(body)


def _seed_pair(path: Path) -> None:
    engine = create_engine("sqlite:///" + path.resolve().as_posix(), poolclass=NullPool)
    Base.metadata.create_all(engine)
    baseline = _summary(p95_ms=10.0, request_throughput_rps=1.0)
    higher = _summary(p95_ms=30.0, request_throughput_rps=2.0)
    zero_p95 = _summary(p95_ms=10.0, request_throughput_rps=2.0)
    with Session(engine) as session:
        save_experiment(session, _empty_run(), _snapshot("gemma3:1b"), baseline)
        save_experiment(session, _empty_run(), _snapshot("other:1b"), higher)
        save_experiment(session, _empty_run(), _snapshot("other:1b"), zero_p95)
        session.commit()
    engine.dispose()


def _summary(*, p95_ms: float, request_throughput_rps: float) -> AggregateSummary:
    return AggregateSummary(
        average_ms=10.0,
        median_ms=10.0,
        p50_ms=10.0,
        p95_ms=p95_ms,
        p99_ms=p95_ms,
        error_rate=0.0,
        generation_throughput_tps=1.0,
        request_throughput_rps=request_throughput_rps,
    )


def _snapshot(model: str) -> ConfigurationSnapshot:
    return ConfigurationSnapshot(
        model=model,
        prompt="Hi",
        num_predict=8,
        warmup_count=0,
        measured_count=1,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.test",
        capture_time=1.0,
        cpu_model="fixture-cpu",
        logical_cpu_count=4,
        total_ram_bytes=8,
        python_version="3.x",
    )


def _empty_run() -> BenchmarkRun:
    return BenchmarkRun(warmup=(), measured=(), concurrency=1)
