"""Routing selection on constructed catalogs.

P95 figures are fixtures. No test asserts a live latency. No test reads a
findings file for an expected timing. No test contacts Ollama.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.routing import may_fallback, route
from app.routing.policies import (
    CatalogEntry,
    Decision,
    LatencyBudget,
    Measurement,
    RouteRequest,
)

_FORBIDDEN = ("better", "worse", "improved", "winner", "recommend", "best")
_PROFILE = "short_prompt_short_output"
_OTHER_PROFILE = "long_prompt_short_output"


def _measurement(
    p95: float | None,
    *,
    average: float | None = None,
) -> Measurement:
    return Measurement(average_ms=average, p95_ms=p95)


def _entry(
    model: str,
    p95: float | None,
    *,
    average: float | None = None,
    capabilities: frozenset[str] = frozenset(),
    size: int | None = None,
    profile: str = _PROFILE,
    also: dict[str, Measurement] | None = None,
) -> CatalogEntry:
    measurements: dict[str, Measurement] = {
        profile: _measurement(p95, average=average),
    }
    if also:
        measurements.update(also)
    return CatalogEntry(
        model=model,
        capabilities=capabilities,
        model_size_bytes=size,
        measurements=measurements,
    )


def _request(
    *,
    profile_name: str = _PROFILE,
    required_capabilities: frozenset[str] = frozenset(),
    max_model_size_bytes: int | None = None,
    latency_budget: LatencyBudget | None = None,
    static_model: str | None = None,
) -> RouteRequest:
    return RouteRequest(
        profile_name=profile_name,
        required_capabilities=required_capabilities,
        max_model_size_bytes=max_model_size_bytes,
        latency_budget=latency_budget,
        static_model=static_model,
    )


def _route(
    policy: str,
    catalog: list[CatalogEntry],
    request: RouteRequest,
    unavailable=(),
) -> Decision:
    decision = route(policy, catalog, request, unavailable)
    lowered = decision.reason.lower()
    for word in _FORBIDDEN:
        assert word not in lowered
    return decision


def test_lowest_stored_p95_for_the_requested_profile_is_selected() -> None:
    catalog = [
        _entry(
            "profile-500",
            500,
            also={_OTHER_PROFILE: _measurement(50)},
        ),
        _entry(
            "profile-200",
            200,
            also={_OTHER_PROFILE: _measurement(900)},
        ),
    ]

    decision = _route("workload_aware", catalog, _request())

    assert decision.selected_model == "profile-200"
    assert decision.stored_p95_ms == 200
    assert decision.in_catalog is True
    assert decision.failed_constraints == ()
    assert decision.preferred_model == "profile-200"
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_equal_p95_keeps_the_earlier_catalog_entry() -> None:
    catalog = [
        _entry("later-in-alphabet", 200),
        _entry("earlier-in-alphabet", 200),
    ]

    decision = _route("workload_aware", catalog, _request())

    assert decision.selected_model == "later-in-alphabet"
    assert decision.stored_p95_ms == 200


def test_required_vision_drops_the_faster_candidate_that_lacks_it() -> None:
    catalog = [
        _entry("no-vision", 100, capabilities=frozenset({"completion"})),
        _entry("has-vision", 400, capabilities=frozenset({"completion", "vision"})),
    ]

    decision = _route(
        "workload_aware",
        catalog,
        _request(required_capabilities=frozenset({"vision"})),
    )

    assert decision.selected_model == "has-vision"
    assert decision.stored_p95_ms == 400


def test_capability_match_is_case_sensitive() -> None:
    catalog = [
        _entry("wrong-case", 100, capabilities=frozenset({"Vision"})),
        _entry("exact-case", 500, capabilities=frozenset({"vision"})),
    ]

    decision = _route(
        "workload_aware",
        catalog,
        _request(required_capabilities=frozenset({"vision"})),
    )

    assert decision.selected_model == "exact-case"


def test_empty_capability_requirement_filters_nothing() -> None:
    catalog = [
        _entry("no-vision", 100),
        _entry("has-vision", 500, capabilities=frozenset({"vision"})),
    ]

    decision = _route("workload_aware", catalog, _request())

    assert decision.selected_model == "no-vision"
    assert decision.stored_p95_ms == 100


def test_size_cap_drops_a_larger_file_and_an_unset_size() -> None:
    catalog = [
        _entry("unset-size", 50, size=None),
        _entry("larger-file", 100, size=801),
        _entry("equal-size", 200, size=800),
    ]

    decision = _route(
        "workload_aware",
        catalog,
        _request(max_model_size_bytes=800),
    )

    assert decision.selected_model == "equal-size"
    assert decision.stored_p95_ms == 200


def test_average_budget_keeps_the_model_under_the_maximum() -> None:
    catalog = [
        _entry("over-average", 200, average=400),
        _entry("under-average", 900, average=100),
    ]
    budget = LatencyBudget("average_ms", 150)

    decision = _route(
        "latency_constrained",
        catalog,
        _request(latency_budget=budget),
    )

    assert decision.selected_model == "under-average"
    assert decision.stored_p95_ms == 900


def test_when_both_averages_pass_the_lower_p95_is_selected() -> None:
    catalog = [
        _entry("higher-p95", 900, average=100),
        _entry("lower-p95", 200, average=140),
    ]

    decision = _route(
        "latency_constrained",
        catalog,
        _request(latency_budget=LatencyBudget("average_ms", 150)),
    )

    assert decision.selected_model == "lower-p95"
    assert decision.stored_p95_ms == 200


def test_static_keeps_the_configured_name_when_capability_fails() -> None:
    catalog = [
        _entry("configured", 500, capabilities=frozenset({"completion"})),
        _entry("other", 200, capabilities=frozenset({"vision"})),
    ]

    decision = _route(
        "static",
        catalog,
        _request(
            required_capabilities=frozenset({"vision"}),
            static_model="configured",
            latency_budget=LatencyBudget("average_ms", 150),
        ),
    )

    assert decision.selected_model == "configured"
    assert decision.in_catalog is True
    assert decision.stored_p95_ms == 500
    assert "capability" in decision.failed_constraints
    assert "latency_budget" not in decision.failed_constraints
    assert decision.selected_model != "other"


def test_static_failure_labels_follow_capability_size_then_p95() -> None:
    catalog = [
        CatalogEntry(
            model="configured",
            capabilities=frozenset({"completion"}),
            model_size_bytes=None,
            measurements={},
        )
    ]

    decision = _route(
        "static",
        catalog,
        _request(
            required_capabilities=frozenset({"vision"}),
            max_model_size_bytes=800,
            static_model="configured",
        ),
    )

    assert decision.selected_model == "configured"
    assert decision.failed_constraints == ("capability", "model_size", "p95_missing")
    assert decision.stored_p95_ms is None


def test_static_returns_a_name_absent_from_the_catalog() -> None:
    catalog = [_entry("present", 200)]

    decision = _route(
        "static",
        catalog,
        _request(static_model="absent"),
    )

    assert decision.selected_model == "absent"
    assert decision.in_catalog is False
    assert decision.stored_p95_ms is None
    assert decision.failed_constraints == ()
    assert decision.preferred_model == "absent"
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_static_requires_a_configured_name() -> None:
    with pytest.raises(ValueError):
        route("static", [_entry("present", 200)], _request())


def test_workload_aware_ignores_a_budget_and_selects_the_lowest_p95() -> None:
    catalog = [
        _entry("over-average", 200, average=400),
        _entry("under-average", 900, average=100),
    ]

    decision = _route(
        "workload_aware",
        catalog,
        _request(latency_budget=LatencyBudget("average_ms", 150)),
    )

    assert decision.selected_model == "over-average"
    assert decision.stored_p95_ms == 200


def test_unknown_profile_matches_no_measurement() -> None:
    catalog = [_entry("only", 200)]

    decision = _route(
        "workload_aware",
        catalog,
        _request(profile_name="not_a_profile"),
    )

    assert decision.selected_model is None
    assert decision.in_catalog is False
    assert decision.stored_p95_ms is None
    assert decision.failed_constraints == ()
    assert decision.preferred_model is None
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_unknown_policy_name_raises() -> None:
    with pytest.raises(ValueError):
        route("not_a_policy", [_entry("only", 200)], _request())


def test_both_available_selects_the_200_ms_model() -> None:
    catalog = [_entry("p95-500", 500), _entry("p95-200", 200)]

    decision = _route("availability_aware", catalog, _request())

    assert decision.selected_model == "p95-200"
    assert decision.stored_p95_ms == 200
    assert decision.preferred_model == "p95-200"
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_unavailable_200_ms_model_selects_500_ms_once() -> None:
    catalog = [_entry("p95-500", 500), _entry("p95-200", 200)]

    decision = _route(
        "availability_aware",
        catalog,
        _request(),
        {"p95-200"},
    )

    assert decision.selected_model == "p95-500"
    assert decision.stored_p95_ms == 500
    assert decision.preferred_model == "p95-200"
    assert decision.fell_back is True
    assert decision.fallback_count == 1
    assert decision.in_catalog is True


def test_static_returns_gemma_when_gemma_is_unavailable() -> None:
    catalog = [_entry("gemma", 500), _entry("other", 200)]

    decision = _route(
        "static",
        catalog,
        _request(static_model="gemma"),
        {"gemma"},
    )

    assert decision.selected_model == "gemma"
    assert decision.preferred_model == "gemma"
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_other_policies_ignore_the_unavailable_set() -> None:
    catalog = [
        _entry("p95-200", 200, average=100),
        _entry("p95-500", 500, average=100),
    ]
    blocked = {"p95-200"}

    workload = _route("workload_aware", catalog, _request(), blocked)
    limited = _route(
        "latency_constrained",
        catalog,
        _request(latency_budget=LatencyBudget("average_ms", 150)),
        blocked,
    )

    assert workload.selected_model == "p95-200"
    assert workload.fell_back is False
    assert workload.fallback_count == 0
    assert limited.selected_model == "p95-200"
    assert limited.fell_back is False
    assert limited.fallback_count == 0


def test_availability_aware_ignores_a_latency_budget() -> None:
    catalog = [
        _entry("p95-200", 200, average=400),
        _entry("p95-500", 500, average=100),
    ]

    decision = _route(
        "availability_aware",
        catalog,
        _request(latency_budget=LatencyBudget("average_ms", 150)),
    )

    assert decision.selected_model == "p95-200"
    assert decision.stored_p95_ms == 200
    assert decision.fell_back is False
    assert decision.fallback_count == 0


def test_availability_aware_miss_is_not_a_fallback() -> None:
    decision = _route("availability_aware", [_entry("unset-p95", None)], _request())

    assert decision.selected_model is None
    assert decision.preferred_model is None
    assert decision.fell_back is False
    assert decision.fallback_count == 0
    assert decision.failed_constraints == ()


def test_skipped_preferred_with_no_remaining_model() -> None:
    catalog = [_entry("p95-500", 500), _entry("p95-200", 200)]

    decision = _route(
        "availability_aware",
        catalog,
        _request(),
        {"p95-200", "p95-500"},
    )

    assert decision.selected_model is None
    assert decision.preferred_model == "p95-200"
    assert decision.fell_back is True
    assert decision.fallback_count == 1
    assert decision.in_catalog is False


def test_latency_constrained_without_a_budget_raises() -> None:
    with pytest.raises(ValueError):
        route("latency_constrained", [_entry("only", 200, average=100)], _request())


def test_budget_metric_outside_the_five_fields_raises() -> None:
    request = _request(latency_budget=LatencyBudget("eval_duration", 150))

    with pytest.raises(ValueError):
        route("latency_constrained", [_entry("only", 200, average=100)], request)


def _measured_row(*, success: bool, error_type: str | None) -> SimpleNamespace:
    return SimpleNamespace(success=success, error_type=error_type)


def test_may_fallback_is_false_for_an_empty_tuple() -> None:
    assert may_fallback(()) is False


def test_may_fallback_is_false_for_a_successful_row() -> None:
    assert may_fallback((_measured_row(success=True, error_type=None),)) is False


def test_may_fallback_is_false_for_a_cancelled_row() -> None:
    cancelled = _measured_row(success=False, error_type="CancelledError")
    failed = _measured_row(success=False, error_type="OllamaTimeoutError")

    assert may_fallback((cancelled,)) is False
    assert may_fallback((failed, cancelled)) is False


def test_may_fallback_is_true_when_every_measured_row_failed() -> None:
    rows = (
        _measured_row(success=False, error_type="OllamaTimeoutError"),
        _measured_row(success=False, error_type="OllamaConnectionError"),
    )

    assert may_fallback(rows) is True


def test_decision_type_has_no_winner_field() -> None:
    decision = _route("workload_aware", [_entry("only", 200)], _request())
    names = {item.name for item in fields(Decision)}
    names.update(item.name for item in fields(decision))

    assert "winner" not in names
    assert "improved" not in names
    assert "recommendation" not in names
    assert "best" not in names


def test_routing_modules_do_not_import_runtime_owners() -> None:
    root = Path(__file__).resolve().parents[2] / "app" / "routing"
    forbidden = {
        "app.inference",
        "app.benchmark",
        "app.database",
        "app.metrics",
        "psutil",
        "sqlite3",
        "sqlalchemy",
    }
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for name in imported:
            assert name not in forbidden
            assert not any(name.startswith(f"{item}.") for item in forbidden)
