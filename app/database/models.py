"""SQLite tables for one stored experiment.

Domain records stay dataclasses. These rows hold the same fields. A request
stores ``success`` and ``error_type``. There is no execution-state column.
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadata for the experiment tables."""


class ExperimentRow(Base):
    """Snapshot fields, the sampling error, and the stored aggregate columns."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sampling_error: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    num_predict: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warmup_count: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_count: Mapped[int] = mapped_column(Integer, nullable=False)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_name: Mapped[str] = mapped_column(String, nullable=False)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
    capture_time: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_model: Mapped[str] = mapped_column(String, nullable=False)
    logical_cpu_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_ram_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    python_version: Mapped[str] = mapped_column(String, nullable=False)
    average_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p50_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    generation_throughput_tps: Mapped[float | None] = mapped_column(Float, nullable=True)
    request_throughput_rps: Mapped[float | None] = mapped_column(Float, nullable=True)


class RequestRow(Base):
    """One warm-up or measured request, in the order it was saved."""

    __tablename__ = "request_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    num_predict: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_start: Mapped[float] = mapped_column(Float, nullable=False)
    first_content_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_end: Mapped[float] = mapped_column(Float, nullable=False)
    end_to_end_ms: Mapped[float] = mapped_column(Float, nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    error_type: Mapped[str | None] = mapped_column(String, nullable=True)
    eval_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_eval_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_eval_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eval_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SampleRow(Base):
    """One resource sample, in the order it was saved."""

    __tablename__ = "resource_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    taken_at: Mapped[float] = mapped_column(Float, nullable=False)
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    system_ram_used_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    system_ram_total_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    process_rss_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
