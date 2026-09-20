"""WebSocket streamer: agent events -> browser, filtered per org (and optionally per run)."""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .auth import ws_principal
from .bus import get_bus
from .config import get_settings
from .models import AgentEvent
from .store import store

router = APIRouter()


@router.websocket("/ws/events")
async def events_ws(ws: WebSocket):
    principal = ws_principal(ws)
    run_filter = ws.query_params.get("run_id")
    await ws.accept()
    topic = get_settings().kafka_topic_events
    bus = get_bus()

    async def pump():
        async for msg in bus.live(topic):
            if msg.get("org_id") != principal.org:
                continue                     # hard tenant isolation
            if run_filter and msg.get("run_id") != run_filter:
                continue
            await ws.send_json(msg)

    task = asyncio.create_task(pump())
    try:
        while True:
            cmd = await ws.receive_json()   # UI -> agents: pause / resume / steer
            if cmd.get("op") in {"pause", "resume", "steer"}:
                await bus.publish(get_settings().kafka_topic_runs,
                                  {"type": f"run.{cmd['op']}", "org_id": principal.org, **cmd})
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()


async def ingest_events():
    """Background task: persist events emitted by the agent swarm."""
    s = get_settings()
    async for msg in get_bus().subscribe(s.kafka_topic_events, "gateway-store", "gw-1"):
        ev = AgentEvent(**msg)
        store.events[ev.run_id].append(ev)
        run = store.runs.get(ev.run_id)
        if run:                                         # keep run cards in sync with agent progress
            if "risk_score" in ev.payload: run.risk_score = ev.payload["risk_score"]
            if ev.agent == "ship" and ev.kind == "patch": run.status = "awaiting_review"
            elif ev.kind == "error": run.status = "failed"
            elif ev.agent in {"architect", "execution", "chaos"}: run.status = {"architect": "planning", "execution": "running", "chaos": "chaos"}[ev.agent]
