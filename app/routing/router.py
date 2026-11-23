"""Dispatch ``route`` to one caller-supplied policy.

``route`` does not call Ollama, does not call ``psutil``, does not open
SQLite, and does not call ``summarize``. It does not name a winner.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.routing.policies import (
    CatalogEntry,
    Decision,
    RouteRequest,
    latency_constrained,
    static,
    workload_aware,
)

_POLICIES = {
    "static": static,
    "workload_aware": workload_aware,
    "latency_constrained": latency_constrained,
}


def route(
    policy: str,
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
) -> Decision:
    """Return the decision for ``policy`` on ``catalog`` and ``request``.

    An unknown policy name raises ``ValueError``. Catalog order is the
    order of ``catalog``.
    """

    chosen = _POLICIES.get(policy)
    if chosen is None:
        raise ValueError(f"unknown policy: {policy}")
    return chosen(catalog, request)
