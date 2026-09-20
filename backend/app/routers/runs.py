from fastapi import APIRouter, Depends, HTTPException
from ..auth import Principal, current_user, require_role
from ..bus import get_bus
from ..config import get_settings
from ..models import Run, RunRequest, RunStatus
from ..store import store

router = APIRouter(prefix="/runs", tags=["runs"])

# Hard server-side ceiling; the UI can ask for more, the API never grants it.
MAX_INTENSITY = 0.3


@router.post("", response_model=Run, status_code=202)
async def create_run(req: RunRequest, p: Principal = Depends(require_role("engineer", "admin"))):
    if req.chaos:
        req.chaos.intensity = min(req.chaos.intensity, MAX_INTENSITY)
    req.autonomy = req.autonomy or get_settings().autonomy_level
    run = Run(org_id=p.org, request=req)
    store.runs[run.id] = run
    await get_bus().publish(get_settings().kafka_topic_runs, {"type": "run.created", **run.model_dump(mode="json")})
    return run


@router.get("", response_model=list[Run])
async def list_runs(p: Principal = Depends(current_user)):
    return store.runs_for(p.org)


@router.get("/{run_id}")
async def get_run(run_id: str, p: Principal = Depends(current_user)):
    run = store.runs.get(run_id)
    if not run or run.org_id != p.org:
        raise HTTPException(404, "run not found")
    return {"run": run, "events": store.events[run_id][-500:]}


@router.post("/{run_id}/kill")
async def kill_run(run_id: str, p: Principal = Depends(require_role("engineer", "admin"))):
    """Global kill-switch: agents poll this and tear down containers immediately."""
    run = store.runs.get(run_id)
    if not run or run.org_id != p.org:
        raise HTTPException(404)
    run.status = RunStatus.failed
    await get_bus().publish(get_settings().kafka_topic_runs, {"type": "run.kill", "run_id": run_id, "org_id": p.org})
    return {"killed": run_id}
