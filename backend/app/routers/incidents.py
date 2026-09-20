"""Incident & Self-Patch Review Console API. Humans approve/reject AI patches here."""
from fastapi import APIRouter, Depends, HTTPException
from ..auth import Principal, current_user, require_role
from ..bus import get_bus
from ..config import get_settings
from ..models import PatchProposal
from ..store import store

router = APIRouter(prefix="/patches", tags=["self-patch"])


@router.get("", response_model=list[PatchProposal])
async def list_patches(p: Principal = Depends(current_user)):
    return store.patches_for(p.org)


@router.post("/internal", response_model=PatchProposal, include_in_schema=False)
async def register_patch(patch: PatchProposal, p: Principal = Depends(require_role("service"))):
    store.patches[patch.id] = patch
    return patch


async def _decide(patch_id: str, org: str, decision: str) -> PatchProposal:
    patch = store.patches.get(patch_id)
    if not patch or patch.org_id != org:
        raise HTTPException(404, "patch not found")
    patch.state = decision  # type: ignore[assignment]
    await get_bus().publish(get_settings().kafka_topic_runs,
                            {"type": f"patch.{decision}", "patch_id": patch_id, "run_id": patch.run_id, "org_id": org})
    return patch


@router.post("/{patch_id}/approve", response_model=PatchProposal)
async def approve(patch_id: str, p: Principal = Depends(require_role("reviewer", "admin"))):
    patch = store.patches.get(patch_id)
    if patch and not patch.verified_in_sandbox:
        raise HTTPException(409, "patch was not verified in sandbox; refusing to approve")
    return await _decide(patch_id, p.org, "approved")


@router.post("/{patch_id}/reject", response_model=PatchProposal)
async def reject(patch_id: str, p: Principal = Depends(require_role("reviewer", "admin"))):
    return await _decide(patch_id, p.org, "rejected")
