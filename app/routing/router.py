"""Dispatch ``route`` to one caller-supplied policy.

``route`` does not call Ollama, does not call ``psutil``, does not open
SQLite, and does not call ``summarize``. It does not name a winner.
Only ``availability_aware`` reads the unavailable set.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from app.routing.policies import (
    CatalogEntry,
    Decision,
    RouteRequest,
    availability_aware,
    latency_constrained,
    static,
    workload_aware,
)

_POLICIES = {
    "static": static,
    "workload_aware": workload_aware,
    "latency_constrained": latency_constrained,
    "availability_aware": availability_aware,
}


def route(
    policy: str,
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
    unavailable: Collection[str] = (),
) -> Decision:
    """Return the decision for ``policy`` on ``catalog`` and ``request``.

    An unknown policy name raises ``ValueError``. Catalog order is the
    order of ``catalog``. ``unavailable`` is a set of model names. Only
    ``availability_aware`` reads it. The other policies ignore it.
    """

    chosen = _POLICIES.get(policy)
    if chosen is None:
        raise ValueError(f"unknown policy: {policy}")
    if policy == "availability_aware":
        return availability_aware(catalog, request, unavailable)
    return chosen(catalog, request)
