"""Select a model from a catalog the caller already filled.

``route`` dispatches to ``static``, ``workload_aware``, and
``latency_constrained``.

This package does not call Ollama, does not call ``psutil``, does not open
SQLite, does not call ``summarize``, and does not name a winner.
"""

from app.routing.policies import (
    CatalogEntry,
    Decision,
    LatencyBudget,
    Measurement,
    RouteRequest,
    latency_constrained,
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
    "latency_constrained",
    "route",
    "static",
    "workload_aware",
]
