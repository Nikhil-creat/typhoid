"""Event bus abstraction: Redis Streams (default) or Kafka. Decouples UI from agent loops."""
from __future__ import annotations
import json
from typing import AsyncIterator, Protocol
import redis.asyncio as aioredis
from .config import get_settings


class Bus(Protocol):
    async def publish(self, topic: str, msg: dict) -> None: ...
    def subscribe(self, topic: str, group: str, consumer: str) -> AsyncIterator[dict]: ...


class RedisBus:
    def __init__(self, url: str):
        self.r = aioredis.from_url(url, decode_responses=True)

    async def publish(self, topic: str, msg: dict) -> None:
        await self.r.xadd(topic, {"d": json.dumps(msg, default=str)}, maxlen=100_000, approximate=True)
        await self.r.publish(f"live:{topic}", json.dumps(msg, default=str))  # fan-out for websockets

    async def subscribe(self, topic: str, group: str, consumer: str):
        try:
            await self.r.xgroup_create(topic, group, id="$", mkstream=True)
        except aioredis.ResponseError:
            pass  # group exists
        while True:
            resp = await self.r.xreadgroup(group, consumer, {topic: ">"}, count=20, block=5000)
            for _, entries in resp or []:
                for entry_id, fields in entries:
                    yield json.loads(fields["d"])
                    await self.r.xack(topic, group, entry_id)   # at-least-once

    async def live(self, topic: str):
        ps = self.r.pubsub()
        await ps.subscribe(f"live:{topic}")
        async for m in ps.listen():
            if m["type"] == "message":
                yield json.loads(m["data"])


class KafkaBus:
    def __init__(self, bootstrap: str):
        self.bootstrap = bootstrap
        self._producer = None

    async def _p(self):
        if not self._producer:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap)
            await self._producer.start()
        return self._producer

    async def publish(self, topic: str, msg: dict) -> None:
        p = await self._p()
        await p.send_and_wait(topic, json.dumps(msg, default=str).encode(),
                              key=msg.get("run_id", "").encode() or None)  # per-run ordering

    async def subscribe(self, topic: str, group: str, consumer: str):
        from aiokafka import AIOKafkaConsumer
        c = AIOKafkaConsumer(topic, bootstrap_servers=self.bootstrap, group_id=group,
                             enable_auto_commit=False)
        await c.start()
        try:
            async for m in c:
                yield json.loads(m.value)
                await c.commit()
        finally:
            await c.stop()

    live = subscribe


_bus: Bus | None = None


def get_bus():
    global _bus
    if _bus is None:
        s = get_settings()
        _bus = KafkaBus(s.kafka_bootstrap) if s.bus_backend == "kafka" else RedisBus(s.redis_url)
    return _bus
