"""HTTP routes.

``POST`` stores a pending job and returns. The task owns the run.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import CompareIn, JobCreate, RouteIn

router = APIRouter(prefix="/api")


@router.post("/jobs")
async def post_job(body: JobCreate, request: Request) -> dict:
    """Store a pending job and return its id without awaiting the stream."""

    return request.app.state.service.submit(body)


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, request: Request) -> dict:
    """Return the job state, the two counts, and the latest sample."""

    try:
        return request.app.state.service.job(job_id)
    except LookupError:
        raise HTTPException(status_code=404) from None


@router.post("/jobs/{job_id}/cancel")
async def post_cancel(job_id: int, request: Request) -> dict:
    """Set the cancel event and return while the task is still winding down."""

    try:
        return request.app.state.service.cancel(job_id)
    except LookupError:
        raise HTTPException(status_code=404) from None


@router.get("/overview")
async def get_overview(request: Request) -> dict:
    """Engines, models, hardware, recent experiments, and the current sample."""

    return await request.app.state.service.overview()


@router.get("/history")
async def get_history(request: Request) -> list:
    """List the dashboard file and the read-only result files."""

    return request.app.state.service.history()


@router.get("/experiments/{source}/{experiment_id}")
async def get_experiment(source: str, experiment_id: int, request: Request) -> dict:
    """Return one stored snapshot, its rows, its samples, and its aggregates."""

    try:
        return request.app.state.service.experiment(source, experiment_id)
    except LookupError:
        raise HTTPException(status_code=404) from None


@router.post("/compare")
async def post_compare(body: CompareIn, request: Request) -> dict:
    """Load two stored experiments and return ``compare``. No winner field."""

    try:
        return request.app.state.service.compare_pair(
            body.baseline.source,
            body.baseline.id,
            body.candidate.source,
            body.candidate.id,
        )
    except LookupError:
        raise HTTPException(status_code=404) from None


@router.post("/route")
async def post_route(body: RouteIn, request: Request) -> dict:
    """Call ``route`` and return that decision. No winner field."""

    try:
        return request.app.state.service.route_call(body)
    except LookupError:
        raise HTTPException(status_code=404) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
