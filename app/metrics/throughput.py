"""Generation throughput and request throughput for one stored run.

Each function reads ``BenchmarkRun.measured`` and returns one number, or no
value when that formula is undefined. Warm-up rows stay out. These functions
do not take an adapter and they do not open a connection. Decode duration
comes from ``decode_duration_ms``. ``eval_duration`` is not the denominator.
"""

from __future__ import annotations

from app.benchmark.records import BenchmarkRun
from app.metrics.latency import decode_duration_ms


def generation_throughput_tps(run: BenchmarkRun) -> float | None:
    """Output tokens divided by summed client decode time, in tokens per second.

    A measured row joins both sums only when it succeeded, decode duration is
    present and positive, and ``eval_count`` is present. One output token
    still counts. A failed row stays out, including one that still carries a
    first-content stamp. No qualifying row leaves the aggregate unset.
    """
    tokens = 0
    decode_seconds = 0.0
    joined = False
    for row in run.measured:
        if not row.success or row.eval_count is None:
            continue
        decode_ms = decode_duration_ms(row)
        if decode_ms is None or decode_ms <= 0:
            continue
        tokens += row.eval_count
        decode_seconds += decode_ms / 1000.0
        joined = True
    if not joined:
        return None
    return tokens / decode_seconds


def request_throughput_rps(run: BenchmarkRun) -> float | None:
    """Completed measured requests divided by the measured window, in requests per second.

    The window is the latest measured ``client_end`` minus the earliest
    measured ``client_start``. Failed and cancelled rows are not completed.
    Their timestamps still set the window. Warm-up timestamps stay out. No
    measured rows, or a window that is not positive, leaves the rate unset.
    Zero completed requests over a positive window is 0.
    """
    if not run.measured:
        return None
    start = min(row.client_start for row in run.measured)
    end = max(row.client_end for row in run.measured)
    window = end - start
    if window <= 0:
        return None
    completed = sum(1 for row in run.measured if row.success)
    return completed / window
