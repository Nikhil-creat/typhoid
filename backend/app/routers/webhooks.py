"""GitHub / GitLab / Jira webhook receivers with signature verification."""
import hashlib, hmac
from fastapi import APIRouter, Header, HTTPException, Request
from ..bus import get_bus
from ..config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github(request: Request, x_hub_signature_256: str = Header(""), x_github_event: str = Header("")):
    s = get_settings()
    body = await request.body()
    mac = "sha256=" + hmac.new(s.github_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, x_hub_signature_256):
        raise HTTPException(401, "bad signature")
    payload = await request.json()
    if x_github_event in {"pull_request", "push", "deployment_status"}:
        await get_bus().publish(s.kafka_topic_runs, {"type": "scm.change", "provider": "github",
                                                     "event": x_github_event, "payload": payload})
    return {"ok": True}


@router.post("/gitlab")
async def gitlab(request: Request, x_gitlab_token: str = Header("")):
    s = get_settings()
    if not hmac.compare_digest(x_gitlab_token, s.gitlab_webhook_secret):
        raise HTTPException(401, "bad token")
    await get_bus().publish(s.kafka_topic_runs, {"type": "scm.change", "provider": "gitlab",
                                                 "payload": await request.json()})
    return {"ok": True}


@router.post("/jira")
async def jira(request: Request):
    await get_bus().publish(get_settings().kafka_topic_runs,
                            {"type": "ticket.event", "provider": "jira", "payload": await request.json()})
    return {"ok": True}
