"""Start one benchmark job and serve stored reads.

The task sets the job status. It calls ``summarize`` only when ``run``
returns and the cancel event is unset. It does not call ``route`` and it
does not start a second model. The stored retry count is 0.
"""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.api.schemas import CatalogEntryIn, RouteIn, RouteRequestIn
from app.benchmark.records import BenchmarkRun, RequestRecord
from app.benchmark.runner import BenchmarkRunner
from app.database.models import Base
from app.database.repository import (
    StoredExperiment,
    create_pending_job,
    finish_job,
    load_experiment,
    load_experiments,
    set_job_status,
    write_job_snapshot,
)
from app.inference.base import InferenceAdapter
from app.metrics.statistics import summarize
from app.monitoring.sampler import ResourceReading, ResourceSample, read_sample
from app.monitoring.snapshot import (
    ConfigurationSnapshot,
    HardwareIdentity,
    build_snapshot,
    capture_hardware,
)
from app.optimization.comparison import Comparison, compare
from app.routing.policies import (
    CatalogEntry,
    Decision,
    LatencyBudget,
    Measurement,
    RouteRequest,
)
from app.routing.router import route

PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

QWEN_MODEL = "qwen3.5:2b"
GEMMA_MODEL = "gemma3:1b"


@dataclass
class LiveJob:
    """The in-memory record ``GET`` reads while a task is in flight."""

    job_id: int
    status: str
    succeeded_count: int
    failed_count: int
    warmup_count: int
    measured_count: int
    model: str
    prompt: str
    num_predict: int | None
    concurrency: int
    profile_name: str | None
    think: bool | None
    num_thread: int | None
    latest_sample: ResourceSample | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    rows: list[RequestRecord] = field(default_factory=list)
    samples: list[ResourceSample] = field(default_factory=list)
    snapshot: ConfigurationSnapshot | None = None
    task: asyncio.Task[None] | None = None


class BenchmarkService:
    """Open the dashboard database, start the runner, and answer reads."""

    def __init__(
        self,
        adapter: InferenceAdapter,
        dashboard_path: Path,
        result_paths: Mapping[str, Path],
        hardware_probe: Callable[[], HardwareIdentity],
        resource_probe: Callable[[], ResourceReading],
        clock: Callable[[], float],
    ) -> None:
        self.adapter = adapter
        self.dashboard_path = dashboard_path
        self.result_paths = dict(result_paths)
        self.hardware_probe = hardware_probe
        self.resource_probe = resource_probe
        self.clock = clock
        self.jobs: dict[int, LiveJob] = {}

    def submit(self, body) -> dict:
        """Store a pending job and schedule the run. Do not await the stream."""

        think = _resolve_think(body.model, body.think)
        warmup_count = 2 if body.warmup_count is None else body.warmup_count
        measured_count = 3 if body.measured_count is None else body.measured_count
        concurrency = 1 if body.concurrency is None else body.concurrency
        with self._session(self.dashboard_path, readonly=False) as session:
            job_id = create_pending_job(
                session,
                model=body.model,
                prompt=body.prompt,
                num_predict=body.num_predict,
                warmup_count=warmup_count,
                measured_count=measured_count,
                concurrency=concurrency,
                profile_name=body.profile_name,
                think=think,
                num_thread=body.num_thread,
                job_status=PENDING,
            )
            session.commit()
        job = LiveJob(
            job_id=job_id,
            status=PENDING,
            succeeded_count=0,
            failed_count=0,
            warmup_count=warmup_count,
            measured_count=measured_count,
            model=body.model,
            prompt=body.prompt,
            num_predict=body.num_predict,
            concurrency=concurrency,
            profile_name=body.profile_name,
            think=think,
            num_thread=body.num_thread,
        )
        self.jobs[job_id] = job
        job.task = asyncio.create_task(self.execute(job_id))
        return {"id": job_id, "job_status": PENDING}

    def job(self, job_id: int) -> dict:
        """Return the state, the counts, and the latest sample or null."""

        live = self.jobs.get(job_id)
        if live is None:
            raise LookupError(f"no job {job_id}")
        return _job_payload(live)

    def cancel(self, job_id: int) -> dict:
        """Set the existing cancel event and return without awaiting the task."""

        live = self.jobs.get(job_id)
        if live is None:
            raise LookupError(f"no job {job_id}")
        live.cancel_event.set()
        return _job_payload(live)

    async def execute(self, job_id: int) -> None:
        """Read the engine, fill the snapshot, then start the one submitted model."""

        job = self.jobs[job_id]
        self._set_status(job, RUNNING)
        try:
            version = await self.adapter.engine_version()
            snapshot = build_snapshot(
                model=job.model,
                prompt=job.prompt,
                num_predict=job.num_predict,
                warmup_count=job.warmup_count,
                measured_count=job.measured_count,
                concurrency=job.concurrency,
                engine_name="ollama",
                engine_version=version,
                clock=self.clock,
                probe=self.hardware_probe,
                profile_name=job.profile_name,
                think=job.think,
                num_thread=job.num_thread,
                retry_count=0,
            )
        except Exception:
            self._set_status(job, FAILED)
            return
        job.snapshot = snapshot
        with self._session(self.dashboard_path, readonly=False) as session:
            write_job_snapshot(session, job.job_id, snapshot, RUNNING)
            session.commit()
        if job.cancel_event.is_set():
            self._finish(job, None, snapshot, None, CANCELLED)
            return
        runner = BenchmarkRunner(self.adapter, clock=self.clock)
        try:
            run = await runner.run(
                job.model,
                job.prompt,
                num_predict=job.num_predict,
                warmup_count=job.warmup_count,
                measured_count=job.measured_count,
                concurrency=job.concurrency,
                profile_name=job.profile_name,
                think=job.think,
                num_thread=job.num_thread,
                cancel_event=job.cancel_event,
                sampler=self._sample,
                progress=lambda item: _accept_progress(job, item),
            )
        except asyncio.CancelledError:
            status = CANCELLED if job.cancel_event.is_set() else FAILED
            self._finish(job, _sink_run(job), snapshot, None, status)
            return
        except Exception:
            status = CANCELLED if job.cancel_event.is_set() else FAILED
            self._finish(job, _sink_run(job), snapshot, None, status)
            return
        if job.cancel_event.is_set():
            self._finish(job, run, snapshot, None, CANCELLED)
            return
        self._finish(job, run, snapshot, summarize(run), COMPLETED)

    async def overview(self) -> dict:
        """Read engines, models, hardware, recent jobs, and the current sample."""

        version = await self.adapter.engine_version()
        models = await self.adapter.list_models()
        hardware = capture_hardware(self.hardware_probe)
        sample = read_sample(self.resource_probe, self.clock)
        recent = list(reversed(self._history_items("dashboard", self.dashboard_path)))
        return {
            "inference_engines": [{"name": "ollama", "version": version}],
            "models": [
                {
                    "name": model.name,
                    "size": model.size,
                    "quantization": model.quantization,
                    "parameter_size": model.parameter_size,
                    "architecture": model.architecture,
                }
                for model in models
            ],
            "hardware": {
                "cpu_model": hardware.cpu_model,
                "logical_cpu_count": hardware.logical_cpu_count,
                "total_ram_bytes": hardware.total_ram_bytes,
                "python_version": hardware.python_version,
            },
            "recent_experiments": recent,
            "sample": _sample_payload(sample),
        }

    def history(self) -> list[dict]:
        """List the dashboard file, then each read-only result file.

        A missing file contributes no rows and is not created. Each item
        carries its source name and its id.
        """

        items = self._history_items("dashboard", self.dashboard_path)
        for source, path in self.result_paths.items():
            items.extend(self._history_items(source, path))
        return items

    def experiment(self, source: str, experiment_id: int) -> dict:
        """Return the stored snapshot, rows, samples, and aggregates."""

        stored = self._load_one(source, experiment_id)
        return _experiment_payload(stored)

    def compare_pair(
        self,
        baseline_source: str,
        baseline_id: int,
        candidate_source: str,
        candidate_id: int,
    ) -> dict:
        """Load both stored experiments and return ``compare``.

        This method does not call the adapter. The sign sentence is included
        only when ``compare`` stored one.
        """

        baseline = self._load_one(baseline_source, baseline_id)
        candidate = self._load_one(candidate_source, candidate_id)
        return _comparison_payload(compare(baseline, candidate))

    def route_call(self, body: RouteIn) -> dict:
        """Call ``route`` and return that decision. This does not call the adapter."""

        catalog = tuple(_catalog_entry(entry) for entry in body.catalog)
        decision = route(
            body.policy,
            catalog,
            _route_request(body.request),
            tuple(body.unavailable),
        )
        return _decision_payload(decision)

    def _sample(self) -> ResourceSample:
        return read_sample(self.resource_probe, self.clock)

    def _set_status(self, job: LiveJob, status: str) -> None:
        with self._session(self.dashboard_path, readonly=False) as session:
            set_job_status(session, job.job_id, status)
            session.commit()
        job.status = status

    def _finish(
        self,
        job: LiveJob,
        run: BenchmarkRun | None,
        snapshot: ConfigurationSnapshot | None,
        summary,
        status: str,
    ) -> None:
        with self._session(self.dashboard_path, readonly=False) as session:
            finish_job(session, job.job_id, run, snapshot, summary, status)
            session.commit()
        job.status = status

    def _history_items(self, source: str, path: Path) -> list[dict]:
        if not path.is_file():
            return []
        with self._session(path, readonly=True) as session:
            stored = load_experiments(session)
        return [_history_item(source, item) for item in stored]

    def _load_one(self, source: str, experiment_id: int) -> StoredExperiment:
        path = self._source_path(source)
        if not path.is_file():
            raise LookupError(f"no stored source {source}")
        with self._session(path, readonly=True) as session:
            return load_experiment(session, experiment_id)

    def _source_path(self, source: str) -> Path:
        if source == "dashboard":
            return self.dashboard_path
        try:
            return self.result_paths[source]
        except KeyError:
            raise LookupError(f"no stored source {source}") from None

    @contextmanager
    def _session(self, path: Path, *, readonly: bool):
        if readonly:
            location = path.resolve().as_posix()
            engine = create_engine(
                "sqlite://",
                creator=lambda: sqlite3.connect(f"file:{location}?mode=ro", uri=True),
                poolclass=NullPool,
            )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(
                "sqlite:///" + path.resolve().as_posix(),
                poolclass=NullPool,
            )
            Base.metadata.create_all(engine)
        try:
            with Session(engine) as session:
                yield session
        finally:
            engine.dispose()


def _resolve_think(model: str, think: bool | None) -> bool | None:
    """Qwen sends false. Gemma omits the flag. Any other model keeps the flag."""

    if model == QWEN_MODEL:
        return False
    if model == GEMMA_MODEL:
        return None
    return think


def _accept_progress(job: LiveJob, item: RequestRecord | ResourceSample) -> None:
    """Count a recorded row, or keep the latest sample. Do not read a status."""

    if isinstance(item, RequestRecord):
        job.rows.append(item)
        if item.success:
            job.succeeded_count += 1
        else:
            job.failed_count += 1
        return
    job.samples.append(item)
    job.latest_sample = item


def _sink_run(job: LiveJob) -> BenchmarkRun:
    """Build a run from the rows and samples the sink already accepted."""

    return BenchmarkRun(
        warmup=tuple(row for row in job.rows if row.phase == "warmup"),
        measured=tuple(row for row in job.rows if row.phase == "measured"),
        concurrency=job.concurrency,
        resource_samples=tuple(job.samples),
        profile_name=job.profile_name,
        think=job.think,
        num_thread=job.num_thread,
    )


def _job_payload(job: LiveJob) -> dict:
    sample = None if job.latest_sample is None else _sample_payload(job.latest_sample)
    return {
        "id": job.job_id,
        "job_status": job.status,
        "succeeded_count": job.succeeded_count,
        "failed_count": job.failed_count,
        "warmup_count": job.warmup_count,
        "measured_count": job.measured_count,
        "latest_sample": sample,
    }


def _sample_payload(sample: ResourceSample) -> dict:
    return {
        "taken_at": sample.taken_at,
        "cpu_percent": sample.cpu_percent,
        "system_ram_used_bytes": sample.system_ram_used_bytes,
        "system_ram_total_bytes": sample.system_ram_total_bytes,
        "process_rss_bytes": sample.process_rss_bytes,
    }


def _history_item(source: str, stored: StoredExperiment) -> dict:
    snapshot = stored.snapshot
    return {
        "source": source,
        "id": stored.experiment_id,
        "job_status": stored.job_status,
        "model": snapshot.model,
        "profile_name": snapshot.profile_name,
        "prompt": snapshot.prompt,
        "num_predict": snapshot.num_predict,
        "warmup_count": snapshot.warmup_count,
        "measured_count": snapshot.measured_count,
        "concurrency": snapshot.concurrency,
        "think": snapshot.think,
        "num_thread": snapshot.num_thread,
    }


def _experiment_payload(stored: StoredExperiment) -> dict:
    return {
        "id": stored.experiment_id,
        "job_status": stored.job_status,
        "snapshot": _snapshot_payload(stored.snapshot),
        "warmup": [_row_payload(row) for row in stored.warmup],
        "measured": [_row_payload(row) for row in stored.measured],
        "resource_samples": [_sample_payload(sample) for sample in stored.resource_samples],
        "sampling_error": stored.sampling_error,
        "summary": {
            "average_ms": stored.summary.average_ms,
            "median_ms": stored.summary.median_ms,
            "p50_ms": stored.summary.p50_ms,
            "p95_ms": stored.summary.p95_ms,
            "p99_ms": stored.summary.p99_ms,
            "error_rate": stored.summary.error_rate,
            "generation_throughput_tps": stored.summary.generation_throughput_tps,
            "request_throughput_rps": stored.summary.request_throughput_rps,
        },
    }


def _snapshot_payload(snapshot: ConfigurationSnapshot) -> dict:
    return {
        "model": snapshot.model,
        "prompt": snapshot.prompt,
        "num_predict": snapshot.num_predict,
        "warmup_count": snapshot.warmup_count,
        "measured_count": snapshot.measured_count,
        "concurrency": snapshot.concurrency,
        "engine_name": snapshot.engine_name,
        "engine_version": snapshot.engine_version,
        "capture_time": snapshot.capture_time,
        "cpu_model": snapshot.cpu_model,
        "logical_cpu_count": snapshot.logical_cpu_count,
        "total_ram_bytes": snapshot.total_ram_bytes,
        "python_version": snapshot.python_version,
        "profile_name": snapshot.profile_name,
        "think": snapshot.think,
        "num_thread": snapshot.num_thread,
        "quantization": snapshot.quantization,
        "parameter_size": snapshot.parameter_size,
        "model_size_bytes": snapshot.model_size_bytes,
        "architecture": snapshot.architecture,
        "routing_policy": snapshot.routing_policy,
        "preferred_model": snapshot.preferred_model,
        "fallback_count": snapshot.fallback_count,
        "retry_count": snapshot.retry_count,
    }


def _row_payload(row: RequestRecord) -> dict:
    return {
        "phase": row.phase,
        "model": row.model,
        "prompt": row.prompt,
        "num_predict": row.num_predict,
        "client_start": row.client_start,
        "first_content_at": row.first_content_at,
        "client_end": row.client_end,
        "end_to_end_ms": row.end_to_end_ms,
        "success": row.success,
        "error_type": row.error_type,
        "eval_count": row.eval_count,
        "prompt_eval_count": row.prompt_eval_count,
        "prompt_eval_duration": row.prompt_eval_duration,
        "eval_duration": row.eval_duration,
    }


def _comparison_payload(result: Comparison) -> dict:
    payload = {
        "baseline_experiment_id": result.baseline_experiment_id,
        "candidate_experiment_id": result.candidate_experiment_id,
        "average_ms_delta": result.average_ms_delta,
        "median_ms_delta": result.median_ms_delta,
        "p50_ms_delta": result.p50_ms_delta,
        "p95_ms_delta": result.p95_ms_delta,
        "p99_ms_delta": result.p99_ms_delta,
        "error_rate_delta": result.error_rate_delta,
        "generation_throughput_tps_delta": result.generation_throughput_tps_delta,
        "request_throughput_rps_delta": result.request_throughput_rps_delta,
        "baseline_phase_label": result.baseline_phase_label,
        "candidate_phase_label": result.candidate_phase_label,
        "setting_differences": [
            {"field": item.field, "baseline": item.baseline, "candidate": item.candidate}
            for item in result.setting_differences
        ],
        "baseline_samples": {
            "sample_count": result.baseline_samples.sample_count,
            "cpu_percent_min": result.baseline_samples.cpu_percent_min,
            "cpu_percent_max": result.baseline_samples.cpu_percent_max,
            "system_ram_used_bytes_min": result.baseline_samples.system_ram_used_bytes_min,
            "system_ram_used_bytes_max": result.baseline_samples.system_ram_used_bytes_max,
        },
        "candidate_samples": {
            "sample_count": result.candidate_samples.sample_count,
            "cpu_percent_min": result.candidate_samples.cpu_percent_min,
            "cpu_percent_max": result.candidate_samples.cpu_percent_max,
            "system_ram_used_bytes_min": result.candidate_samples.system_ram_used_bytes_min,
            "system_ram_used_bytes_max": result.candidate_samples.system_ram_used_bytes_max,
        },
    }
    if result.sign_sentence is not None:
        payload["sign_sentence"] = result.sign_sentence
    return payload


def _decision_payload(decision: Decision) -> dict:
    return {
        "policy": decision.policy,
        "selected_model": decision.selected_model,
        "in_catalog": decision.in_catalog,
        "stored_p95_ms": decision.stored_p95_ms,
        "failed_constraints": list(decision.failed_constraints),
        "reason": decision.reason,
        "preferred_model": decision.preferred_model,
        "fell_back": decision.fell_back,
        "fallback_count": decision.fallback_count,
    }


def _catalog_entry(entry: CatalogEntryIn) -> CatalogEntry:
    measurements = {
        name: Measurement(
            average_ms=measurement.average_ms,
            median_ms=measurement.median_ms,
            p50_ms=measurement.p50_ms,
            p95_ms=measurement.p95_ms,
            p99_ms=measurement.p99_ms,
        )
        for name, measurement in entry.measurements.items()
    }
    return CatalogEntry(
        model=entry.model,
        capabilities=frozenset(entry.capabilities),
        model_size_bytes=entry.model_size_bytes,
        measurements=measurements,
    )


def _route_request(body: RouteRequestIn) -> RouteRequest:
    budget = None
    if body.latency_budget is not None:
        budget = LatencyBudget(metric=body.latency_budget.metric, maximum=body.latency_budget.maximum)
    return RouteRequest(
        profile_name=body.profile_name,
        required_capabilities=frozenset(body.required_capabilities),
        max_model_size_bytes=body.max_model_size_bytes,
        latency_budget=budget,
        static_model=body.static_model,
    )
