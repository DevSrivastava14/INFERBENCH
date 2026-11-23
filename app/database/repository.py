"""Save one experiment and load the stored values back.

``save_experiment`` writes the snapshot, every request row, the resource
samples, and the aggregate columns. ``load_experiment`` returns those stored
values. ``load_experiments`` returns every stored experiment in ascending id
order, using that same mapping. Neither load calls ``summarize``, ``ttft_ms``,
or ``tpot_ms``. They do not rank percentiles, and they do not recompute
throughput.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.benchmark.records import BenchmarkRun, RequestRecord
from app.database.models import ExperimentRow, RequestRow, SampleRow
from app.metrics.statistics import AggregateSummary
from app.monitoring.sampler import ResourceSample
from app.monitoring.snapshot import ConfigurationSnapshot


@dataclass(frozen=True)
class StoredExperiment:
    """The snapshot, rows, samples, and summary read back from one row id.

    ``summary`` is the stored aggregate. Unset fields are null. It is not a
    new calculation.
    """

    experiment_id: int
    snapshot: ConfigurationSnapshot
    warmup: tuple[RequestRecord, ...]
    measured: tuple[RequestRecord, ...]
    resource_samples: tuple[ResourceSample, ...]
    sampling_error: str | None
    summary: AggregateSummary


def save_experiment(
    session: Session,
    run: BenchmarkRun,
    snapshot: ConfigurationSnapshot,
    summary: AggregateSummary | None = None,
) -> int:
    """Write one experiment and return its id.

    ``summary`` may be absent. Absent and unset metric fields are stored as
    null. ``profile_name`` is the snapshot's name, and a missing name is
    stored as null. ``think`` false is stored as false. An omitted think flag
    is stored as null. ``num_thread`` is the snapshot's value. An omitted
    thread value is stored as null. A stored 4 is stored as 4. Quantization,
    parameter size, model size, and architecture are the snapshot's values.
    This function does not call
    ``summarize``, ``ttft_ms``, or ``tpot_ms``, does not call an adapter, and
    does not sample the machine. The caller commits.
    """

    stored = summary if summary is not None else AggregateSummary(
        average_ms=None,
        median_ms=None,
        p50_ms=None,
        p95_ms=None,
        p99_ms=None,
        error_rate=None,
        generation_throughput_tps=None,
        request_throughput_rps=None,
    )
    experiment = ExperimentRow(
        sampling_error=run.sampling_error,
        model=snapshot.model,
        prompt=snapshot.prompt,
        num_predict=snapshot.num_predict,
        warmup_count=snapshot.warmup_count,
        measured_count=snapshot.measured_count,
        concurrency=snapshot.concurrency,
        engine_name=snapshot.engine_name,
        engine_version=snapshot.engine_version,
        capture_time=snapshot.capture_time,
        cpu_model=snapshot.cpu_model,
        logical_cpu_count=snapshot.logical_cpu_count,
        total_ram_bytes=snapshot.total_ram_bytes,
        python_version=snapshot.python_version,
        profile_name=snapshot.profile_name,
        think=snapshot.think,
        num_thread=snapshot.num_thread,
        quantization=snapshot.quantization,
        parameter_size=snapshot.parameter_size,
        model_size_bytes=snapshot.model_size_bytes,
        architecture=snapshot.architecture,
        average_ms=stored.average_ms,
        median_ms=stored.median_ms,
        p50_ms=stored.p50_ms,
        p95_ms=stored.p95_ms,
        p99_ms=stored.p99_ms,
        error_rate=stored.error_rate,
        generation_throughput_tps=stored.generation_throughput_tps,
        request_throughput_rps=stored.request_throughput_rps,
    )
    session.add(experiment)
    session.flush()
    for ordinal, record in enumerate(run.warmup + run.measured):
        session.add(_request_row(experiment.id, ordinal, record))
    for ordinal, sample in enumerate(run.resource_samples):
        session.add(_sample_row(experiment.id, ordinal, sample))
    session.flush()
    return experiment.id


def load_experiment(session: Session, experiment_id: int) -> StoredExperiment:
    """Return the stored snapshot, rows, samples, and aggregate fields.

    Warm-up and measured rows stay apart, in the order they were saved.
    Unset aggregate fields stay null. A column that is absent from an older
    stored file loads as null. This function does not alter that file. It
    does not rank percentiles and does not recompute throughput.
    """

    experiment = _experiment_record(session, experiment_id)
    if experiment is None:
        raise LookupError(f"no stored experiment {experiment_id}")
    request_rows = session.scalars(
        select(RequestRow)
        .where(RequestRow.experiment_id == experiment_id)
        .order_by(RequestRow.ordinal)
    ).all()
    sample_rows = session.scalars(
        select(SampleRow)
        .where(SampleRow.experiment_id == experiment_id)
        .order_by(SampleRow.ordinal)
    ).all()
    records = tuple(_request_record(row) for row in request_rows)
    return StoredExperiment(
        experiment_id=experiment.id,
        snapshot=_snapshot(experiment),
        warmup=tuple(record for record in records if record.phase == "warmup"),
        measured=tuple(record for record in records if record.phase == "measured"),
        resource_samples=tuple(_sample(row) for row in sample_rows),
        sampling_error=experiment.sampling_error,
        summary=AggregateSummary(
            average_ms=experiment.average_ms,
            median_ms=experiment.median_ms,
            p50_ms=experiment.p50_ms,
            p95_ms=experiment.p95_ms,
            p99_ms=experiment.p99_ms,
            error_rate=experiment.error_rate,
            generation_throughput_tps=experiment.generation_throughput_tps,
            request_throughput_rps=experiment.request_throughput_rps,
        ),
    )


def _experiment_record(session: Session, experiment_id: int) -> SimpleNamespace | None:
    """Read one experiment row. A column missing from the file stays null."""

    present = _stored_column_names(session, "experiments")
    mapped = [column.name for column in ExperimentRow.__table__.columns]
    selected = [name for name in mapped if name in present]
    if "id" not in selected:
        raise LookupError("stored experiments table has no id column")
    statement = text(
        "SELECT "
        + ", ".join(selected)
        + " FROM experiments WHERE id = :experiment_id"
    )
    row = session.execute(statement, {"experiment_id": experiment_id}).mappings().first()
    if row is None:
        return None
    values = {name: None for name in mapped}
    values.update(row)
    if values["think"] is not None:
        values["think"] = bool(values["think"])
    return SimpleNamespace(**values)


def _stored_column_names(session: Session, table: str) -> set[str]:
    rows = session.execute(text(f"PRAGMA table_info({table})")).all()
    return {row[1] for row in rows}


def load_experiments(session: Session) -> tuple[StoredExperiment, ...]:
    """Return every stored experiment in ascending id order.

    Each item uses the same row mapping as ``load_experiment``. Unset
    aggregates stay null. This function does not call ``summarize``,
    ``ttft_ms``, or ``tpot_ms``.
    """

    experiment_ids = session.scalars(select(ExperimentRow.id).order_by(ExperimentRow.id)).all()
    return tuple(load_experiment(session, experiment_id) for experiment_id in experiment_ids)


def _request_row(experiment_id: int, ordinal: int, record: RequestRecord) -> RequestRow:
    return RequestRow(
        experiment_id=experiment_id,
        ordinal=ordinal,
        phase=record.phase,
        model=record.model,
        prompt=record.prompt,
        num_predict=record.num_predict,
        client_start=record.client_start,
        first_content_at=record.first_content_at,
        client_end=record.client_end,
        end_to_end_ms=record.end_to_end_ms,
        success=record.success,
        error_type=record.error_type,
        eval_count=record.eval_count,
        prompt_eval_count=record.prompt_eval_count,
        prompt_eval_duration=record.prompt_eval_duration,
        eval_duration=record.eval_duration,
    )


def _sample_row(experiment_id: int, ordinal: int, sample: ResourceSample) -> SampleRow:
    return SampleRow(
        experiment_id=experiment_id,
        ordinal=ordinal,
        taken_at=sample.taken_at,
        cpu_percent=sample.cpu_percent,
        system_ram_used_bytes=sample.system_ram_used_bytes,
        system_ram_total_bytes=sample.system_ram_total_bytes,
        process_rss_bytes=sample.process_rss_bytes,
    )


def _snapshot(experiment: ExperimentRow) -> ConfigurationSnapshot:
    return ConfigurationSnapshot(
        model=experiment.model,
        prompt=experiment.prompt,
        num_predict=experiment.num_predict,
        warmup_count=experiment.warmup_count,
        measured_count=experiment.measured_count,
        concurrency=experiment.concurrency,
        engine_name=experiment.engine_name,
        engine_version=experiment.engine_version,
        capture_time=experiment.capture_time,
        cpu_model=experiment.cpu_model,
        logical_cpu_count=experiment.logical_cpu_count,
        total_ram_bytes=experiment.total_ram_bytes,
        python_version=experiment.python_version,
        profile_name=experiment.profile_name,
        think=experiment.think,
        num_thread=experiment.num_thread,
        quantization=experiment.quantization,
        parameter_size=experiment.parameter_size,
        model_size_bytes=experiment.model_size_bytes,
        architecture=experiment.architecture,
    )


def _request_record(row: RequestRow) -> RequestRecord:
    phase = row.phase
    if phase not in ("warmup", "measured"):
        raise LookupError(f"stored request phase {phase!r} is not warmup or measured")
    return RequestRecord(
        phase=phase,
        model=row.model,
        prompt=row.prompt,
        num_predict=row.num_predict,
        client_start=row.client_start,
        first_content_at=row.first_content_at,
        client_end=row.client_end,
        end_to_end_ms=row.end_to_end_ms,
        success=bool(row.success),
        error_type=row.error_type,
        eval_count=row.eval_count,
        prompt_eval_count=row.prompt_eval_count,
        prompt_eval_duration=row.prompt_eval_duration,
        eval_duration=row.eval_duration,
    )


def _sample(row: SampleRow) -> ResourceSample:
    return ResourceSample(
        taken_at=row.taken_at,
        cpu_percent=row.cpu_percent,
        system_ram_used_bytes=row.system_ram_used_bytes,
        system_ram_total_bytes=row.system_ram_total_bytes,
        process_rss_bytes=row.process_rss_bytes,
    )
