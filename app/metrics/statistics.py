"""Average, median, percentiles, and error rate for one stored run.

Each function reads ``BenchmarkRun.measured`` and returns one number, or no
value when that formula is undefined. Warm-up rows stay out. These functions
do not take an adapter and they do not open a connection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.benchmark.records import BenchmarkRun, RequestRecord


@dataclass(frozen=True)
class AggregateSummary:
    """Aggregates for one run. Unset fields are formulas that do not apply.

    The two throughput fields come from ``app.metrics.throughput``. This
    object does not belong on ``BenchmarkRun``.
    """

    average_ms: float | None
    median_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    error_rate: float | None
    generation_throughput_tps: float | None
    request_throughput_rps: float | None


def average_ms(run: BenchmarkRun) -> float | None:
    """Arithmetic mean of successful measured end-to-end latencies."""
    sample = _latency_sample(run)
    if not sample:
        return None
    return sum(sample) / len(sample)


def median_ms(run: BenchmarkRun) -> float | None:
    """Ordinary median of the latency sample.

    Odd counts use the middle value. Even counts use the mean of the two
    middle values, which can differ from nearest-rank P50.
    """
    sample = sorted(_latency_sample(run))
    count = len(sample)
    if count == 0:
        return None
    middle = count // 2
    if count % 2 == 1:
        return sample[middle]
    return (sample[middle - 1] + sample[middle]) / 2.0


def percentile_ms(run: BenchmarkRun, percent: int) -> float | None:
    """Nearest-rank percentile of the latency sample.

    Rank is ``ceil(percent * n / 100)``, 1-based, clamped to ``1..n``. The
    result is an observed end-to-end latency. An empty sample returns no value.
    """
    sample = sorted(_latency_sample(run))
    count = len(sample)
    if count == 0:
        return None
    rank = math.ceil(percent * count / 100)
    if rank < 1:
        rank = 1
    if rank > count:
        rank = count
    return sample[rank - 1]


def error_rate(run: BenchmarkRun) -> float | None:
    """Failed measured requests divided by measured requests that were not cancelled.

    ``CancelledError`` is outside both counts. No measured rows, or only
    cancellations, leaves the rate unset. Zero failures on a non-empty
    population is 0.
    """
    population = _error_population(run)
    if not population:
        return None
    failed = sum(1 for row in population if not row.success)
    return failed / len(population)


def summarize(run: BenchmarkRun) -> AggregateSummary:
    """Fill one summary from the measured rows, including both throughputs."""
    from app.metrics.throughput import (
        generation_throughput_tps,
        request_throughput_rps,
    )

    return AggregateSummary(
        average_ms=average_ms(run),
        median_ms=median_ms(run),
        p50_ms=percentile_ms(run, 50),
        p95_ms=percentile_ms(run, 95),
        p99_ms=percentile_ms(run, 99),
        error_rate=error_rate(run),
        generation_throughput_tps=generation_throughput_tps(run),
        request_throughput_rps=request_throughput_rps(run),
    )


def _latency_sample(run: BenchmarkRun) -> list[float]:
    """Successful measured end-to-end latencies. Failures and cancellations stay out."""
    values: list[float] = []
    for row in run.measured:
        if not row.success or row.error_type == "CancelledError":
            continue
        values.append(row.end_to_end_ms)
    return values


def _error_population(run: BenchmarkRun) -> list[RequestRecord]:
    """Measured rows that are not cancellations."""
    return [row for row in run.measured if row.error_type != "CancelledError"]
