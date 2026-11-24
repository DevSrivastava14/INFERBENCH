"""Request bodies for the benchmark caller.

``num_ctx`` is not a field. ``think`` true is rejected.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class JobCreate(BaseModel):
    """One benchmark submission.

    Blank warm-up, measured count, and concurrency are filled by the caller
    as 2, 3, and 1. Blank ``num_thread`` stays unset.
    """

    model_config = ConfigDict(extra="ignore")

    model: str
    prompt: str
    num_predict: int | None = None
    warmup_count: int | None = None
    measured_count: int | None = None
    concurrency: int | None = None
    profile_name: str | None = None
    think: bool | None = None
    num_thread: int | None = None

    @field_validator("model", "prompt")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty")
        return value

    @field_validator("concurrency")
    @classmethod
    def reject_concurrency_below_one(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("concurrency must be 1 or greater")
        return value

    @field_validator("think")
    @classmethod
    def reject_think_true(cls, value: bool | None) -> bool | None:
        if value is True:
            raise ValueError("think true does not start a job")
        return value

    @field_validator("profile_name")
    @classmethod
    def blank_profile_is_unset(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        return value


class MeasurementIn(BaseModel):
    """Stored latency fields the caller already has."""

    model_config = ConfigDict(extra="ignore")

    average_ms: float | None = None
    median_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    p99_ms: float | None = None


class CatalogEntryIn(BaseModel):
    """One catalog model. Latency fields are copied, not recomputed."""

    model_config = ConfigDict(extra="ignore")

    model: str
    capabilities: list[str] = []
    model_size_bytes: int | None = None
    measurements: dict[str, MeasurementIn] = {}


class LatencyBudgetIn(BaseModel):
    """One stored latency field and a maximum."""

    model_config = ConfigDict(extra="ignore")

    metric: str
    maximum: float


class RouteRequestIn(BaseModel):
    """The request fields ``route`` already accepts."""

    model_config = ConfigDict(extra="ignore")

    profile_name: str
    required_capabilities: list[str] = []
    max_model_size_bytes: int | None = None
    latency_budget: LatencyBudgetIn | None = None
    static_model: str | None = None


class RouteIn(BaseModel):
    """A policy, a catalog, the request, and unavailable names."""

    model_config = ConfigDict(extra="ignore")

    policy: str
    catalog: list[CatalogEntryIn]
    request: RouteRequestIn
    unavailable: list[str] = []


class SourceRef(BaseModel):
    """One stored experiment, named by its file and its id."""

    model_config = ConfigDict(extra="ignore")

    source: str
    id: int


class CompareIn(BaseModel):
    """Two stored experiments. The caller names both."""

    model_config = ConfigDict(extra="ignore")

    baseline: SourceRef
    candidate: SourceRef
