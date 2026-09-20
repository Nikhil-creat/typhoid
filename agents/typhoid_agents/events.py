"""Emit AgentEvents so the dashboard sees every thought/tool/result live."""
import json
from datetime import datetime, timezone
import redis.asyncio as aioredis
from .settings import settings

_r = None


def _redis():
    global _r
    if _r is None:
        _r = aioredis.from_url(settings().redis_url, decode_responses=True)
    return _r


async def emit(state: dict, agent: str, kind: str, **payload) -> None:
    msg = {"run_id": state["run_id"], "org_id": state["org_id"], "agent": agent, "kind": kind,
           "payload": payload, "ts": datetime.now(timezone.utc).isoformat()}
    topic = settings().kafka_topic_events
    r = _redis()
    await r.xadd(topic, {"d": json.dumps(msg, default=str)}, maxlen=100_000, approximate=True)
    await r.publish(f"live:{topic}", json.dumps(msg, default=str))


async def is_killed(state: dict) -> bool:
    return bool(await _redis().sismember("typhoid:killed", state["run_id"]))
