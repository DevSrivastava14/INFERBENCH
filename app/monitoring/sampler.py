"""One CPU and RAM sample.

The reader calls an injectable probe. It does not call Ollama and it does
not compute a latency. The real probe uses a non-blocking CPU read.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSample:
    """One sample taken on the runner clock.

    ``cpu_percent`` is system-wide at this instant. System RAM is the whole
    machine. ``process_rss_bytes`` is this benchmark process. These fields
    are not TTFT, TPOT, end-to-end latency, or a throughput.
    """

    taken_at: float
    cpu_percent: float
    system_ram_used_bytes: int
    system_ram_total_bytes: int
    process_rss_bytes: int


@dataclass(frozen=True)
class ResourceReading:
    """The four numbers a resource probe returns. No clock."""

    cpu_percent: float
    system_ram_used_bytes: int
    system_ram_total_bytes: int
    process_rss_bytes: int


def read_sample(
    probe: Callable[[], ResourceReading],
    clock: Callable[[], float],
) -> ResourceSample:
    """Map one probe reading onto a sample.

    ``clock`` is the runner clock. ``taken_at`` is that reading. The first
    non-blocking CPU value may be 0. That 0 is stored as the sample.
    """

    reading = probe()
    return ResourceSample(
        taken_at=clock(),
        cpu_percent=reading.cpu_percent,
        system_ram_used_bytes=reading.system_ram_used_bytes,
        system_ram_total_bytes=reading.system_ram_total_bytes,
        process_rss_bytes=reading.process_rss_bytes,
    )


def psutil_probe() -> ResourceReading:
    """Read system CPU, system RAM, and this process RSS.

    ``cpu_percent`` is called with no blocking interval. This function does
    not look for an Ollama process.
    """

    import psutil

    memory = psutil.virtual_memory()
    return ResourceReading(
        cpu_percent=psutil.cpu_percent(interval=None),
        system_ram_used_bytes=int(memory.used),
        system_ram_total_bytes=int(memory.total),
        process_rss_bytes=int(psutil.Process().memory_info().rss),
    )
