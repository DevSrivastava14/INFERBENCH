"""FastAPI entry.

``create_app`` is the caller the tests build with a fake adapter.
``create_production_app`` points new runs at the dashboard database and
leaves the four result files read-only.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

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
    app.add_exception_handler(SQLAlchemyError, _database_error)
    app.add_exception_handler(sqlite3.Error, _database_error)
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


def _database_error(_request: Request, _exc: Exception) -> JSONResponse:
    """Return an error with no summary and no latency.

    A failed read or write does not fill in an aggregate or a clock.
    """

    return JSONResponse(status_code=500, content={"detail": "database error"})


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


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def listen_settings(environ: Mapping[str, str] | None = None) -> tuple[str, int]:
    """Return the listen host and port.

    An absent or blank ``INFERBENCH_HOST`` keeps ``127.0.0.1``. An absent or
    blank ``INFERBENCH_PORT`` keeps ``8000``. The container is the caller that
    sets the host to ``0.0.0.0``.
    """

    env = os.environ if environ is None else environ
    host = env.get("INFERBENCH_HOST")
    if host is None or not host.strip():
        host = DEFAULT_HOST
    else:
        host = host.strip()
    raw_port = env.get("INFERBENCH_PORT")
    if raw_port is None or not str(raw_port).strip():
        port = DEFAULT_PORT
    else:
        port = int(str(raw_port).strip())
    return host, port


def main() -> None:
    """Listen on the local port the dashboard proxies to."""

    import uvicorn

    host, port = listen_settings()
    uvicorn.run(create_production_app(), host=host, port=port)


if __name__ == "__main__":
    main()
