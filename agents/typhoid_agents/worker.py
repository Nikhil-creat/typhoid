"""Swarm worker: consumes run.created from the bus, drives the LangGraph, honours kill/pause/steer."""
import asyncio, json, logging, os, socket
import redis.asyncio as aioredis
from .graph import build_graph, make_checkpointer
from .settings import settings

log = logging.getLogger("typhoid.worker")


async def handle(graph, msg: dict, r):
    t = msg.get("type")
    if t == "run.kill":
        await r.sadd("typhoid:killed", msg["run_id"]); return
    if t != "run.created":
        return
    req = msg["request"]
    state = {"run_id": msg["id"], "org_id": msg["org_id"], "repo": req["repo"], "ref": req["ref"],
             "target_url": req["target_url"], "user_story": req.get("user_story"),
             "mockup_b64": req.get("mockup_b64"), "chaos": req.get("chaos"),
             "autonomy": req.get("autonomy", "review"), "patch_attempts": 0}
    cfg = {"configurable": {"thread_id": msg["id"]}}          # checkpoint per run → resumable after crash
    await graph.ainvoke(state, cfg)


async def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    s = settings()
    r = aioredis.from_url(s.redis_url, decode_responses=True)
    graph = build_graph(await make_checkpointer())
    topic, group, me = s.kafka_topic_runs, "swarm", socket.gethostname()
    try: await r.xgroup_create(topic, group, id="$", mkstream=True)
    except aioredis.ResponseError: pass
    sem = asyncio.Semaphore(4)                                 # concurrent runs per worker

    async def guarded(m):
        async with sem:
            try: await handle(graph, m, r)
            except Exception: log.exception("run failed")

    log.info("swarm worker %s ready", me)
    while True:
        for _, entries in await r.xreadgroup(group, me, {topic: ">"}, count=10, block=5000) or []:
            for eid, f in entries:
                asyncio.create_task(guarded(json.loads(f["d"])))
                await r.xack(topic, group, eid)


if __name__ == "__main__":
    asyncio.run(main())
