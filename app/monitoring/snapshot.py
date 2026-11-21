"""Hardware identity and the configuration snapshot.

``build_snapshot`` reads an injectable probe and an injectable clock. It
does not call Ollama and it does not start a benchmark.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareIdentity:
    """CPU model, logical CPU count, total RAM, and the Python version."""

    cpu_model: str
    logical_cpu_count: int
    total_ram_bytes: int
    python_version: str


@dataclass(frozen=True)
class ConfigurationSnapshot:
    """The fields stored for one experiment configuration.

    ``engine_version`` is the string the caller passed. This object does not
    fetch it.
    """

    model: str
    prompt: str
    num_predict: int | None
    warmup_count: int
    measured_count: int
    concurrency: int
    engine_name: str
    engine_version: str
    capture_time: float
    cpu_model: str
    logical_cpu_count: int
    total_ram_bytes: int
    python_version: str


def capture_hardware(probe: Callable[[], HardwareIdentity]) -> HardwareIdentity:
    """Return the CPU model, logical CPU count, total RAM, and Python version."""

    reading = probe()
    return HardwareIdentity(
        cpu_model=reading.cpu_model,
        logical_cpu_count=reading.logical_cpu_count,
        total_ram_bytes=reading.total_ram_bytes,
        python_version=reading.python_version,
    )


def build_snapshot(
    *,
    model: str,
    prompt: str,
    num_predict: int | None,
    warmup_count: int,
    measured_count: int,
    concurrency: int,
    engine_name: str,
    engine_version: str,
    clock: Callable[[], float],
    probe: Callable[[], HardwareIdentity],
) -> ConfigurationSnapshot:
    """Combine caller fields with hardware from ``probe``.

    Capture time is one reading of ``clock``. Engine name and engine version
    are the strings the caller passed.
    """

    hardware = capture_hardware(probe)
    return ConfigurationSnapshot(
        model=model,
        prompt=prompt,
        num_predict=num_predict,
        warmup_count=warmup_count,
        measured_count=measured_count,
        concurrency=concurrency,
        engine_name=engine_name,
        engine_version=engine_version,
        capture_time=clock(),
        cpu_model=hardware.cpu_model,
        logical_cpu_count=hardware.logical_cpu_count,
        total_ram_bytes=hardware.total_ram_bytes,
        python_version=hardware.python_version,
    )


def psutil_hardware_probe() -> HardwareIdentity:
    """Read this machine's CPU model, logical CPU count, total RAM, and Python."""

    import platform

    import psutil

    count = psutil.cpu_count(logical=True)
    if count is None:
        raise RuntimeError("logical CPU count is unavailable")
    return HardwareIdentity(
        cpu_model=platform.processor(),
        logical_cpu_count=count,
        total_ram_bytes=int(psutil.virtual_memory().total),
        python_version=platform.python_version(),
    )
