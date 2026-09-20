"""Natural-language & Visual Test Studio: story/mockup -> executable test plan preview."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..auth import Principal, current_user
from ..bus import get_bus
from ..config import get_settings

router = APIRouter(prefix="/studio", tags=["studio"])


class StoryIn(BaseModel):
    story: str
    target_url: str
    mockup_b64: str | None = None


@router.post("/compile")
async def compile_story(body: StoryIn, p: Principal = Depends(current_user)):
    """Ask the Architect agent to compile a story into a plan (async; result arrives on the WS)."""
    await get_bus().publish(get_settings().kafka_topic_runs,
                            {"type": "studio.compile", "org_id": p.org, **body.model_dump()})
    return {"accepted": True}
