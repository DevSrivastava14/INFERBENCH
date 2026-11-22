"""Resource samples and the hardware snapshot.

The probe, the clock, and the engine version are fixtures. Ollama is not
contacted. No test asserts a live CPU percent or a live RSS.
"""

from __future__ import annotations

from app.monitoring.sampler import ResourceReading, ResourceSample, read_sample
from app.monitoring.snapshot import HardwareIdentity, build_snapshot


def test_read_sample_maps_a_fake_probe() -> None:
    def probe() -> ResourceReading:
        return ResourceReading(
            cpu_percent=0.0,
            system_ram_used_bytes=11,
            system_ram_total_bytes=22,
            process_rss_bytes=33,
        )

    sample = read_sample(probe, lambda: 7.0)

    assert sample == ResourceSample(
        taken_at=7.0,
        cpu_percent=0.0,
        system_ram_used_bytes=11,
        system_ram_total_bytes=22,
        process_rss_bytes=33,
    )


def test_build_snapshot_copies_injected_hardware_and_engine_version() -> None:
    calls: list[str] = []
    hardware = HardwareIdentity(
        cpu_model="fixture-cpu",
        logical_cpu_count=8,
        total_ram_bytes=99,
        python_version="3.x",
    )

    def probe() -> HardwareIdentity:
        calls.append("probe")
        return hardware

    def clock() -> float:
        calls.append("clock")
        return 5.0

    snapshot = build_snapshot(
        model="gemma3:1b",
        prompt="Hi",
        num_predict=8,
        warmup_count=1,
        measured_count=1,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.test",
        clock=clock,
        probe=probe,
    )

    assert calls == ["probe", "clock"]
    assert "connect" not in build_snapshot.__code__.co_names
    assert snapshot.cpu_model == "fixture-cpu"
    assert snapshot.logical_cpu_count == 8
    assert snapshot.total_ram_bytes == 99
    assert snapshot.python_version == "3.x"
    assert snapshot.engine_name == "ollama"
    assert snapshot.engine_version == "0.test"
    assert snapshot.capture_time == 5.0
    assert snapshot.model == "gemma3:1b"
    assert snapshot.prompt == "Hi"
    assert snapshot.num_predict == 8
    assert snapshot.profile_name is None


def test_build_snapshot_stores_a_profile_name() -> None:
    hardware = HardwareIdentity(
        cpu_model="fixture-cpu",
        logical_cpu_count=8,
        total_ram_bytes=99,
        python_version="3.x",
    )
    snapshot = build_snapshot(
        model="gemma3:1b",
        prompt="Hi",
        num_predict=32,
        warmup_count=2,
        measured_count=3,
        concurrency=1,
        engine_name="ollama",
        engine_version="0.test",
        clock=lambda: 5.0,
        probe=lambda: hardware,
        profile_name="long_prompt_short_output",
    )

    assert snapshot.profile_name == "long_prompt_short_output"
