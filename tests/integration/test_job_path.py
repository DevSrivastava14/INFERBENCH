"""One job through the app, the runner, the summary, and a reload.

The client is the FastAPI app on an in-memory transport. It does not start
a live server and it does not contact Ollama. The adapter is the unit-test
fake. No test reads a findings file for an expected timing.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.benchmark.records import BenchmarkRun
from app.core.exceptions import ModelNotInstalledError
from app.database.repository import load_experiment
from app.metrics.statistics import summarize
from tests.unit.test_api import FakeAdapter, _build, _client, _wait_status

SUMMARY_FIELDS = (
    "average_ms",
    "median_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "error_rate",
    "generation_throughput_tps",
    "request_throughput_rps",
)


def _reload(dashboard: Path, job_id: int):
    engine = create_engine("sqlite:///" + dashboard.resolve().as_posix(), poolclass=NullPool)
    with Session(engine) as session:
        loaded = load_experiment(session, job_id)
    engine.dispose()
    return loaded


@pytest.mark.asyncio
async def test_held_stream_completes_and_the_reload_matches(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.hold = True
    app, dashboard = _build(tmp_path, adapter)
    async with _client(app) as client:
        posted = await client.post("/api/jobs", json={"model": "gemma3:1b", "prompt": "Hi"})
        assert posted.status_code == 200
        job_id = posted.json()["id"]
        await asyncio.wait_for(adapter.started.wait(), timeout=2)
        running = await client.get(f"/api/jobs/{job_id}")
        assert running.json()["job_status"] == "RUNNING"
        adapter.release.set()
        completed = await _wait_status(client, job_id, "COMPLETED")
        experiment = await client.get(f"/api/experiments/dashboard/{job_id}")

    assert completed["job_status"] == "COMPLETED"
    assert experiment.status_code == 200
    loaded = _reload(dashboard, job_id)
    expected = summarize(
        BenchmarkRun(
            warmup=loaded.warmup,
            measured=loaded.measured,
            concurrency=loaded.snapshot.concurrency,
        )
    )
    assert loaded.job_status == "COMPLETED"
    assert loaded.summary == expected
    stored = experiment.json()["summary"]
    for name in SUMMARY_FIELDS:
        assert stored[name] == getattr(loaded.summary, name)


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
        finished = await _wait_status(client, job_id, "CANCELLED")

    assert finished["job_status"] == "CANCELLED"
    loaded = _reload(dashboard, job_id)
    assert loaded.job_status == "CANCELLED"


@pytest.mark.asyncio
async def test_missing_model_never_calls_generate_stream(tmp_path: Path) -> None:
    adapter = FakeAdapter()
    adapter.show_error = ModelNotInstalledError("gemma3:1b")
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
        finished = await _wait_status(client, posted.json()["id"], "FAILED")

    assert finished["job_status"] == "FAILED"
    assert adapter.stream_calls == 0
    loaded = _reload(dashboard, posted.json()["id"])
    assert loaded.job_status == "FAILED"
    assert loaded.measured == ()
