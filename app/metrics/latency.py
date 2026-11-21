"""TTFT, decode duration, and TPOT from one stored request row.

Each function reads a ``RequestRecord`` and returns one number, or no value
when that formula is undefined. They do not take an adapter and they do not
open a connection. A provider ``eval_count`` is used as given. It is not
labeled an estimate.
"""

from __future__ import annotations

from app.benchmark.records import RequestRecord


def ttft_ms(record: RequestRecord) -> float | None:
    """Milliseconds from client start to the first-content stamp."""
    stamp = _stamp(record)
    if stamp is None:
        return None
    return (stamp - record.client_start) * 1000.0


def decode_duration_ms(record: RequestRecord) -> float | None:
    """Milliseconds from the first-content stamp to client end.

    This is not ``eval_duration``.
    """
    stamp = _stamp(record)
    if stamp is None:
        return None
    return (record.client_end - stamp) * 1000.0


def tpot_ms(record: RequestRecord) -> float | None:
    """Decode duration divided by output tokens minus one.

    Undefined when ``eval_count`` is missing or below 2. TTFT and decode
    duration stay available from their own functions in that case.
    """
    decode = decode_duration_ms(record)
    if decode is None:
        return None
    count = record.eval_count
    if count is None or count < 2:
        return None
    return decode / (count - 1)


def _stamp(record: RequestRecord) -> float | None:
    """The first-content stamp, or no value on a failed or cancelled row."""
    if not record.success or record.error_type is not None:
        return None
    return record.first_content_at
