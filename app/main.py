"""FastAPI entry.

``create_app`` is the caller the tests build with a fake adapter.
``create_production_app`` points new runs at the dashboard database and
leaves the four result files read-only.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.api.service import BenchmarkService
from app.core.config import OllamaConfig
from app.inference.base import InferenceAdapter
from app.inference.ollama import OllamaAdapter
from app.monitoring.sampler import ResourceReading, psutil_probe
from app.monitoring.snapshot import HardwareIdentity, psutil_hardware_probe


def create_app(
    *,
    adapter: InferenceAdapter,
    dashboard_path: Path,
    result_paths: Mapping[str, Path] | None = None,
    hardware_probe: Callable[[], HardwareIdentity],
    resource_probe: Callable[[], ResourceReading],
    clock: Callable[[], float] | None = None,
) -> FastAPI:
    """Build the API around the adapter, the database path, and the probes."""

    app = FastAPI()
    app.state.service = BenchmarkService(
        adapter=adapter,
        dashboard_path=dashboard_path,
        result_paths={} if result_paths is None else result_paths,
        hardware_probe=hardware_probe,
        resource_probe=resource_probe,
        clock=time.perf_counter if clock is None else clock,
    )
    app.include_router(router)
    return app


def create_production_app() -> FastAPI:
    """Use the local Ollama adapter and the probes on this machine.

    New runs use ``experiments/results/dashboard.sqlite``. The four existing
    result files are read-only. A missing result file is not created.
    """

    root = Path(__file__).resolve().parents[1]
    results = root / "experiments" / "results"
    return create_app(
        adapter=OllamaAdapter(OllamaConfig.from_env()),
        dashboard_path=results / "dashboard.sqlite",
        result_paths={
            "workload-sensitivity": results / "workload-sensitivity.sqlite",
            "model-comparison": results / "model-comparison.sqlite",
            "serving-config": results / "serving-config.sqlite",
            "routing-effectiveness": results / "routing-effectiveness.sqlite",
        },
        hardware_probe=psutil_hardware_probe,
        resource_probe=psutil_probe,
    )


def main() -> None:
    """Listen on the local port the dashboard proxies to."""

    import uvicorn

    uvicorn.run(create_production_app(), host="127.0.0.1", port=8000)
