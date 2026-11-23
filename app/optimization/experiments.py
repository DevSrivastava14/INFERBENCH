"""Phase label for one stored experiment.

The label is the larger client-clock share on successful measured rows.
This module does not call Ollama, does not call ``psutil``, does not open
SQLite, and does not call ``summarize``.
"""

from __future__ import annotations

from typing import Literal

from app.database.repository import StoredExperiment
from app.metrics.latency import decode_duration_ms, ttft_ms

PhaseLabel = Literal["prefill", "decode", "even"]


def phase_label(experiment: StoredExperiment) -> PhaseLabel | None:
    """Return ``prefill``, ``decode``, ``even``, or no value.

    Successful measured rows are the only rows that can join. A warm-up row
    stays out. A failed row stays out. A cancelled row stays out. A row joins
    only when ``ttft_ms`` and ``decode_duration_ms`` both return a value.
    The larger sum is the label. Equal sums greater than zero return
    ``even``. No qualifying row returns no value. Both sums equal to zero
    return no value. This function does not read ``eval_duration``.
    """

    prefill_sum = 0.0
    decode_sum = 0.0
    joined = 0
    for record in experiment.measured:
        if record.phase != "measured" or not record.success or record.error_type is not None:
            continue
        prefill = ttft_ms(record)
        decode = decode_duration_ms(record)
        if prefill is None or decode is None:
            continue
        prefill_sum += prefill
        decode_sum += decode
        joined += 1
    if joined == 0:
        return None
    if prefill_sum == decode_sum:
        if prefill_sum > 0:
            return "even"
        return None
    if prefill_sum > decode_sum:
        return "prefill"
    return "decode"
