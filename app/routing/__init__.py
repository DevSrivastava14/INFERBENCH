"""Select a model from a catalog the caller already filled.

``route`` dispatches to ``static``, ``workload_aware``,
``latency_constrained``, and ``availability_aware``. ``may_fallback``
reads measured rows the caller passes.

This package does not call Ollama, does not call ``psutil``, does not open
SQLite, does not call ``summarize``, and does not name a winner.
"""

from app.routing.policies import (
    CatalogEntry,
    Decision,
    LatencyBudget,
    Measurement,
    RouteRequest,
    availability_aware,
    latency_constrained,
    may_fallback,
    static,
    workload_aware,
)
from app.routing.router import route

__all__ = [
    "CatalogEntry",
    "Decision",
    "LatencyBudget",
    "Measurement",
    "RouteRequest",
    "availability_aware",
    "latency_constrained",
    "may_fallback",
    "route",
    "static",
    "workload_aware",
]
