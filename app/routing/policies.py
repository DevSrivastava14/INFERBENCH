"""Pure selection policies over a catalog the caller already filled.

``static`` returns the configured model. ``workload_aware`` selects the
lowest stored P95 for the requested profile among candidates that pass the
capability and size filters. ``latency_constrained`` adds the caller's
budget as a further filter, then uses that same P95 rank.
``availability_aware`` uses that same rank as the preferred model, then
selects the next eligible model when the preferred model is unavailable.
``may_fallback`` reads measured rows the caller passes.

This module does not call Ollama, does not call ``psutil``, does not open
SQLite, and does not call ``summarize``. It does not name a winner.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

LATENCY_FIELDS = (
    "average_ms",
    "median_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
)


@dataclass(frozen=True)
class Measurement:
    """One stored aggregate for one profile.

    Each field is present or unset. The caller copies these numbers. This
    type does not recompute them.
    """

    average_ms: float | None = None
    median_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


@dataclass(frozen=True)
class CatalogEntry:
    """One model the caller placed in the catalog.

    ``model_size_bytes`` unset is not the integer 0. ``measurements`` maps
    a profile name to a stored aggregate. An unknown profile matches nothing.
    """

    model: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    model_size_bytes: int | None = None
    measurements: Mapping[str, Measurement] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.capabilities, str):
            raise TypeError("capabilities is a set of strings")
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        object.__setattr__(self, "measurements", dict(self.measurements))


@dataclass(frozen=True)
class LatencyBudget:
    """One stored latency field and a maximum.

    ``metric`` is one of the five latency field names. The stored value must
    be present and less than or equal to ``maximum``.
    """

    metric: str
    maximum: float


@dataclass(frozen=True)
class RouteRequest:
    """What the caller asks the router to select.

    A latency budget is unset unless the caller sets one. ``static_model``
    is the configured name for the static policy.
    """

    profile_name: str
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    max_model_size_bytes: int | None = None
    latency_budget: LatencyBudget | None = None
    static_model: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.required_capabilities, str):
            raise TypeError("required_capabilities is a set of strings")
        object.__setattr__(
            self,
            "required_capabilities",
            frozenset(self.required_capabilities),
        )


@dataclass(frozen=True)
class Decision:
    """The policy's selection.

    ``stored_p95_ms`` is the P95 the rank used, or the static model's stored
    P95 when that value is present. ``preferred_model`` is the first choice
    when one exists. ``fell_back`` and ``fallback_count`` record one
    replacement. This type has no winner, improved, recommendation, or best
    field.
    """

    policy: str
    selected_model: str | None
    in_catalog: bool
    stored_p95_ms: float | None
    failed_constraints: tuple[str, ...]
    reason: str
    preferred_model: str | None = None
    fell_back: bool = False
    fallback_count: int = 0


def static(catalog: Sequence[CatalogEntry], request: RouteRequest) -> Decision:
    """Return the configured model name.

    A missing configured name raises ``ValueError``. The decision keeps that
    name when a capability check, a size check, or a P95 check fails, and
    lists those failures in that order. A latency budget is ignored. A name
    absent from the catalog is still returned, with ``in_catalog`` false and
    an empty failure list. This policy does not switch to another model.
    """

    if request.static_model is None:
        raise ValueError("static policy requires a configured model name")
    selected = request.static_model
    entry = _find(catalog, selected)
    if entry is None:
        return Decision(
            policy="static",
            selected_model=selected,
            in_catalog=False,
            stored_p95_ms=None,
            failed_constraints=(),
            reason="static policy returns the configured model absent from the catalog",
            preferred_model=selected,
            fell_back=False,
            fallback_count=0,
        )
    return Decision(
        policy="static",
        selected_model=selected,
        in_catalog=True,
        stored_p95_ms=_stored_p95(entry, request.profile_name),
        failed_constraints=_static_failures(entry, request),
        reason="static policy returns the configured model",
        preferred_model=selected,
        fell_back=False,
        fallback_count=0,
    )


def workload_aware(catalog: Sequence[CatalogEntry], request: RouteRequest) -> Decision:
    """Select the lowest stored P95 for the requested profile.

    Candidates must have every required capability and pass the size cap.
    A missing P95 is not selected. Equal P95 keeps the earlier catalog entry.
    No eligible model returns a decision with no selected model and an empty
    failure list. A latency budget on the request is ignored.
    """

    chosen = _lowest_p95(catalog, request, budget=None)
    if chosen is None:
        return _no_selection("workload_aware")
    entry, p95 = chosen
    return _selection("workload_aware", entry, p95)


def latency_constrained(
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
) -> Decision:
    """Filter by the caller's budget, then select the lowest stored P95.

    The budget is one of the five latency field names and a maximum. A
    missing budget, or a metric name outside those five fields, raises
    ``ValueError``. No eligible model returns no selection.
    """

    budget = _require_budget(request)
    chosen = _lowest_p95(catalog, request, budget)
    if chosen is None:
        return _no_selection("latency_constrained")
    entry, p95 = chosen
    return _selection("latency_constrained", entry, p95)


def availability_aware(
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
    unavailable: Collection[str] = (),
) -> Decision:
    """Select the workload-aware model, or the next eligible name.

    The preferred model is the lowest stored P95 among candidates that pass
    the capability and size filters. A latency budget on the request is
    ignored. A name in ``unavailable`` is skipped after that rank. One skip
    sets ``fell_back`` and ``fallback_count`` 1. A miss with no preferred
    model is not a fallback. This policy does not retry the same model.
    """

    blocked = set(unavailable)
    preferred = _lowest_p95(catalog, request, budget=None)
    if preferred is None:
        return _no_selection("availability_aware")
    entry, p95 = preferred
    if entry.model not in blocked:
        return _selection("availability_aware", entry, p95)
    remaining = [item for item in catalog if item.model not in blocked]
    chosen = _lowest_p95(remaining, request, budget=None)
    if chosen is None:
        return _no_selection(
            "availability_aware",
            preferred_model=entry.model,
            fell_back=True,
            fallback_count=1,
        )
    next_entry, next_p95 = chosen
    return Decision(
        policy="availability_aware",
        selected_model=next_entry.model,
        in_catalog=True,
        stored_p95_ms=next_p95,
        failed_constraints=(),
        reason="availability_aware selected the next eligible model",
        preferred_model=entry.model,
        fell_back=True,
        fallback_count=1,
    )


def may_fallback(measured: Sequence[object]) -> bool:
    """Return whether those measured rows may be replaced by another model.

    True only when ``measured`` is non-empty, every row failed, and no row
    has ``error_type`` ``CancelledError``. One successful row returns false.
    One cancelled row returns false. An empty sequence returns false. This
    helper does not call Ollama and does not import the runner.
    """

    if len(measured) == 0:
        return False
    for row in measured:
        if getattr(row, "success"):
            return False
        if getattr(row, "error_type") == "CancelledError":
            return False
    return True


def _require_budget(request: RouteRequest) -> LatencyBudget:
    budget = request.latency_budget
    if budget is None:
        raise ValueError("latency_constrained requires a latency budget")
    if budget.metric not in LATENCY_FIELDS:
        raise ValueError("latency budget metric is outside the stored latency fields")
    return budget


def _find(catalog: Sequence[CatalogEntry], model: str) -> CatalogEntry | None:
    for entry in catalog:
        if entry.model == model:
            return entry
    return None


def _has_capabilities(entry: CatalogEntry, required: frozenset[str]) -> bool:
    return required <= entry.capabilities


def _within_size(entry: CatalogEntry, maximum: int) -> bool:
    if entry.model_size_bytes is None:
        return False
    return entry.model_size_bytes <= maximum


def _static_failures(entry: CatalogEntry, request: RouteRequest) -> tuple[str, ...]:
    failures: list[str] = []
    if not _has_capabilities(entry, request.required_capabilities):
        failures.append("capability")
    if request.max_model_size_bytes is not None and not _within_size(
        entry,
        request.max_model_size_bytes,
    ):
        failures.append("model_size")
    if _stored_p95(entry, request.profile_name) is None:
        failures.append("p95_missing")
    return tuple(failures)


def _stored_p95(entry: CatalogEntry, profile_name: str) -> float | None:
    measurement = entry.measurements.get(profile_name)
    if measurement is None:
        return None
    return measurement.p95_ms


def _passes_budget(
    entry: CatalogEntry,
    request: RouteRequest,
    budget: LatencyBudget,
) -> bool:
    measurement = entry.measurements.get(request.profile_name)
    if measurement is None:
        return False
    stored = getattr(measurement, budget.metric)
    if stored is None:
        return False
    return stored <= budget.maximum


def _lowest_p95(
    catalog: Sequence[CatalogEntry],
    request: RouteRequest,
    budget: LatencyBudget | None,
) -> tuple[CatalogEntry, float] | None:
    chosen: tuple[CatalogEntry, float] | None = None
    for entry in catalog:
        if not _has_capabilities(entry, request.required_capabilities):
            continue
        if request.max_model_size_bytes is not None and not _within_size(
            entry,
            request.max_model_size_bytes,
        ):
            continue
        if budget is not None and not _passes_budget(entry, request, budget):
            continue
        p95 = _stored_p95(entry, request.profile_name)
        if p95 is None:
            continue
        if chosen is None or p95 < chosen[1]:
            chosen = (entry, p95)
    return chosen


def _selection(policy: str, entry: CatalogEntry, p95: float) -> Decision:
    return Decision(
        policy=policy,
        selected_model=entry.model,
        in_catalog=True,
        stored_p95_ms=p95,
        failed_constraints=(),
        reason=f"{policy} selected the lowest stored p95 for the requested profile",
        preferred_model=entry.model,
        fell_back=False,
        fallback_count=0,
    )


def _no_selection(
    policy: str,
    *,
    preferred_model: str | None = None,
    fell_back: bool = False,
    fallback_count: int = 0,
) -> Decision:
    return Decision(
        policy=policy,
        selected_model=None,
        in_catalog=False,
        stored_p95_ms=None,
        failed_constraints=(),
        reason=f"{policy} selected no model",
        preferred_model=preferred_model,
        fell_back=fell_back,
        fallback_count=fallback_count,
    )
