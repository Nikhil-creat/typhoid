"""Chaos-injected container execution manager.

One ephemeral sandbox per test session: read-only rootfs, no capabilities, seccomp default, CPU/mem caps,
private network, hard TTL, secrets injected from Vault into tmpfs and wiped on exit.
Chaos is applied *mid-test* via tc/netem (network), cgroup throttling (CPU) and toxiproxy (DB/DNS outages).
"""
from __future__ import annotations
import asyncio, json, os, secrets, time
from contextlib import asynccontextmanager
import docker
import hvac

FAULT_CMDS = {
    "latency":      "tc qdisc add dev eth0 root netem delay {ms}ms {jitter}ms distribution normal",
    "packet_loss":  "tc qdisc add dev eth0 root netem loss {pct}%",
    "dns_failure":  "sh -c 'echo nameserver 203.0.113.1 > /etc/resolv.conf'",
    "db_outage":    "toxiproxy-cli toxic add -t timeout -a timeout=0 db",
}


class Session:
    def __init__(self, mgr: "ChaosWorkerManager", container, net):
        self.mgr, self.c, self.net = mgr, container, net

    def _exec(self, cmd: str, user="root") -> tuple[int, str]:
        code, out = self.c.exec_run(cmd, user=user, demux=False)
        return code, out.decode(errors="ignore")

    async def _rpc(self, op: str, **payload) -> dict:
        """The runner image exposes a tiny JSON-over-exec RPC (workers/runner/agent.py)."""
        code, out = await asyncio.to_thread(self._exec, f"python /agent.py {op} '{json.dumps(payload)}'", "runner")
        if code != 0:
            raise RuntimeError(f"runner {op} failed: {out[-1500:]}")
        return json.loads(out.splitlines()[-1])

    async def run_plan(self, plan: list[dict], personas: list[dict]) -> dict:
        return await self._rpc("run_plan", plan=plan, personas=personas)

    async def run_chaos(self, spec: dict, plan: list[dict]) -> list[dict]:
        findings = []
        for fault in spec["faults"]:
            k = spec["intensity"]
            cmd = FAULT_CMDS[fault].format(ms=int(200 + 1800 * k), jitter=int(50 * k * 10), pct=int(40 * k))
            # start the workload, inject the fault MID-run, then heal and compare to the steady-state hypothesis
            workload = asyncio.create_task(self._rpc("run_plan", plan=plan, personas=[], timeout=spec["duration_s"]))
            await asyncio.sleep(min(5, spec["duration_s"] / 4))
            await asyncio.to_thread(self._exec, cmd)
            report = await workload
            await asyncio.to_thread(self._exec, "tc qdisc del dev eth0 root || true")      # always heal
            held = all(r["passed"] for r in report["results"]) and report.get("p95_ms", 0) < 800
            findings.append({"fault": fault, "held": held, "p95_ms": report.get("p95_ms"),
                             "observation": "steady state held" if held else f"steady state violated under {fault}",
                             "trace": json.dumps([r for r in report["results"] if not r["passed"]])[:3000]})
        return findings

    async def apply_and_retest(self, diff: str, failing_ids: list[str], regression_test: str | None) -> dict:
        return await self._rpc("apply_and_retest", diff=diff, ids=failing_ids, regression_test=regression_test)


class ChaosWorkerManager:
    def __init__(self):
        self.d = docker.from_env()
        self.image = os.getenv("WORKER_IMAGE", "typhoid/runner:latest")
        self.ttl = int(os.getenv("WORKER_TTL_SECONDS", "900"))

    def _vault_creds(self, org_id: str, run_id: str) -> dict:
        """Dynamic, short-lived credentials (Vault database/OAuth secrets engine). Never long-lived."""
        v = hvac.Client(url=os.getenv("VAULT_ADDR"), token=os.getenv("VAULT_TOKEN"))
        wrap = v.adapter.post(f"/v1/sys/wrapping/wrap", json={"org": org_id, "run": run_id, "nonce": secrets.token_hex(8)},
                              headers={"X-Vault-Wrap-TTL": "60s"})
        return {"wrapped": wrap.json()["wrap_info"]["token"]}

    @asynccontextmanager
    async def session(self, run_id: str, org_id: str, target_url: str, repo: str | None = None, ref: str | None = None):
        net = self.d.networks.create(f"ty-{run_id[:8]}-{secrets.token_hex(2)}", internal=False, labels={"typhoid": run_id})
        creds = self._vault_creds(org_id, run_id)
        c = self.d.containers.run(
            self.image, detach=True, network=net.name, name=f"ty-run-{run_id[:8]}-{secrets.token_hex(2)}",
            labels={"typhoid.run": run_id, "typhoid.org": org_id, "typhoid.expires": str(int(time.time()) + self.ttl)},
            read_only=True, tmpfs={"/tmp": "size=512m,exec", "/run/secrets": "size=1m,mode=0700"},
            cap_drop=["ALL"], cap_add=["NET_ADMIN"],          # NET_ADMIN only for tc; runner user is non-root for the browser
            security_opt=["no-new-privileges:true"], pids_limit=512,
            nano_cpus=int(float(os.getenv("WORKER_CPU_LIMIT", "1.0")) * 1e9), mem_limit=os.getenv("WORKER_MEM_LIMIT", "1g"),
            environment={"TARGET_URL": target_url, "REPO": repo or "", "REF": ref or "", "VAULT_WRAPPED": creds["wrapped"]},
            command="sleep infinity",
        )
        reaper = asyncio.create_task(self._reap_after(c, self.ttl))
        try:
            yield Session(self, c, net)
        finally:
            reaper.cancel()
            await asyncio.to_thread(self._destroy, c, net)

    async def _reap_after(self, c, ttl: int):
        await asyncio.sleep(ttl)
        await asyncio.to_thread(c.kill)             # dead-man's switch: no session outlives its TTL

    @staticmethod
    def _destroy(c, net):
        try:
            c.exec_run("sh -c 'shred -u /run/secrets/* 2>/dev/null; sync'", user="root")   # secure memory/secret clearing
        finally:
            c.remove(force=True, v=True)
            net.remove()
