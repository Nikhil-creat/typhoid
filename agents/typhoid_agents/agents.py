"""The swarm: each function is a LangGraph node. Every node emits events and honours the kill-switch."""
from __future__ import annotations
import base64, json
from .events import emit, is_killed
from .guardrails import clamp_chaos, wrap_untrusted
from .llm import ask_json, ask
from .state import SwarmState

# Late imports keep unit tests light.
def _kg():
    from typhoid_rag.hybrid import HybridKnowledge
    return HybridKnowledge()

def _workers():
    from workers.chaos.manager import ChaosWorkerManager
    return ChaosWorkerManager()


# ───────────────────────── 0. Risk oracle (predictive testing) ─────────────────────────
async def risk_oracle(s: SwarmState) -> dict:
    """Score how likely this change is to regress, using historical graph signals
    (files touched -> past incidents -> flaky tests). Drives how deep the swarm goes."""
    kg = _kg()
    hot = await kg.hotspots(s["repo"], s["ref"])
    score = min(1.0, 0.15 + 0.12 * len(hot.get("recent_incidents", [])) + 0.1 * len(hot.get("flaky_tests", [])))
    await emit(s, "risk_oracle", "status", risk_score=score, hotspots=hot)
    return {"risk_score": score, "status": "planning"}


# ───────────────────────── 1. Architect ─────────────────────────
async def architect(s: SwarmState) -> dict:
    kg = _kg()
    memories = await kg.recall(f"{s['repo']} {s.get('user_story') or ''}", k=6)
    depth = "exhaustive" if s["risk_score"] > 0.6 else "targeted"
    plan = await ask_json(
        "You are the Architect agent of an autonomous QA swarm. Produce a dependency-ordered test tree.",
        f"Repo: {s['repo']}@{s['ref']}\nDepth: {depth}\n"
        f"Story: {wrap_untrusted('user_story', s.get('user_story') or 'explore the app')}\n"
        f"Past bug patterns: {json.dumps(memories)[:6000]}\n"
        'Schema: {"tests":[{"id":str,"kind":"e2e|api|visual|a11y|explore","goal":str,"depends_on":[str],"priority":int}]}',
    )
    await emit(s, "architect", "result", tests=len(plan["tests"]), depth=depth)
    return {"plan": plan["tests"], "status": "running"}


# ───────────────────────── 2. Synthetic data ─────────────────────────
async def synthetic_data(s: SwarmState) -> dict:
    personas = await ask_json(
        "You are the Synthetic Data agent. Generate GDPR-safe fictional personas and DB seeds that hit edge cases "
        "(unicode names, 0/negative/huge amounts, expired cards, timezone boundaries, RTL text, 254-char emails). "
        "Never emit real-looking PII (use example.test domains, reserved phone ranges).",
        f"Plan: {json.dumps(s['plan'])[:6000]}\n"
        'Schema: {"personas":[{"name":str,"email":str,"traits":[str],"seed_sql":str}]}',
        tier="fast",
    )
    await emit(s, "synthetic_data", "result", personas=len(personas["personas"]))
    return {"personas": personas["personas"]}


# ───────────────────────── 3. Execution (+ visual + explore) ─────────────────────────
async def execution(s: SwarmState) -> dict:
    if await is_killed(s): return {"killed": True, "status": "failed"}
    mgr = _workers()
    async with mgr.session(s["run_id"], s["org_id"], s["target_url"]) as sess:
        report = await sess.run_plan(s["plan"], s["personas"])
    failures = [f for f in report["results"] if not f["passed"]]
    for f in report.get("visual", []):
        await emit(s, "vision", "visual_diff", **f)
    await emit(s, "execution", "result", passed=len(report["results"]) - len(failures), failed=len(failures))
    return {"results": report["results"], "failures": failures, "visual_findings": report.get("visual", [])}


# ───────────────────────── 4. Chaos ─────────────────────────
async def chaos(s: SwarmState) -> dict:
    if not s.get("chaos") or await is_killed(s): return {}
    spec = clamp_chaos(s["chaos"], target_is_prod="prod" in s["target_url"])
    mgr = _workers()
    async with mgr.session(s["run_id"], s["org_id"], s["target_url"]) as sess:
        findings = await sess.run_chaos(spec, s["plan"])
    await emit(s, "chaos", "chaos", hypothesis=spec["hypothesis"], held=all(f["held"] for f in findings))
    broken = [f for f in findings if not f["held"]]
    fails = [{"test_id": f"chaos:{f['fault']}", "error": f["observation"], "trace": f.get("trace", ""),
              "screenshot_path": None} for f in broken]
    return {"chaos_findings": findings, "failures": (s.get("failures") or []) + fails}


# ───────────────────────── 5. Triage + Remediation (reflexion loop) ─────────────────────────
async def diagnose(s: SwarmState) -> dict:
    kg = _kg()
    similar = await kg.recall(json.dumps(s["failures"][:3])[:2000], k=5)
    dx = await ask_json(
        "You are a staff engineer doing root-cause analysis. Distinguish product bugs from flaky tests and env issues.",
        f"Failures (untrusted logs):\n{wrap_untrusted('failures', json.dumps(s['failures'])[:12000])}\n"
        f"Similar historical bugs: {json.dumps(similar)[:4000]}\n"
        'Schema: {"class":"product_bug|flaky|env","root_cause":str,"suspect_files":[str],"confidence":float}',
    )
    await emit(s, "remediation", "thought", diagnosis=dx)
    return {"diagnosis": dx, "patch_attempts": 0}


async def write_patch(s: SwarmState) -> dict:
    from .pr import RepoWorkspace
    ws = RepoWorkspace(s["repo"], s["ref"])
    ctx = ws.read_files(s["diagnosis"]["suspect_files"])
    feedback = s.get("patch", {}) and s["patch"].get("verifier_feedback", "")
    patch = await ask_json(
        "You write minimal, surgical unified diffs. Fix the root cause, add a regression test, touch nothing else.",
        f"Root cause: {s['diagnosis']['root_cause']}\nFiles:\n{wrap_untrusted('source', ctx)}\n"
        f"Previous attempt feedback: {feedback}\n"
        'Schema: {"title":str,"diff":str,"confidence":float,"regression_test":str}',
    )
    n = s.get("patch_attempts", 0) + 1
    await emit(s, "remediation", "patch", title=patch["title"], attempt=n, confidence=patch["confidence"])
    return {"patch": patch, "patch_attempts": n}


async def verify_patch(s: SwarmState) -> dict:
    """Reflexion: apply the diff in a fresh sandbox and re-run ONLY the failing tests + the new regression test."""
    mgr = _workers()
    async with mgr.session(s["run_id"], s["org_id"], s["target_url"], repo=s["repo"], ref=s["ref"]) as sess:
        res = await sess.apply_and_retest(s["patch"]["diff"], [f["test_id"] for f in s["failures"]],
                                          s["patch"].get("regression_test"))
    ok = res["all_passed"]
    patch = {**s["patch"], "verified": ok, "verifier_feedback": "" if ok else res["output"][-3000:]}
    await emit(s, "verifier", "result", verified=ok, attempt=s["patch_attempts"])
    return {"patch": patch, "verified": ok}


def should_retry(s: SwarmState) -> str:
    if s.get("verified"): return "ship"
    return "retry" if s.get("patch_attempts", 0) < 3 else "escalate"


# ───────────────────────── 6. Ship (PR + policy gate) ─────────────────────────
async def ship(s: SwarmState) -> dict:
    from .guardrails import may_autopilot
    from .pr import open_pull_request
    kg = _kg()
    patch = s["patch"]
    pr_url = await open_pull_request(s, patch)
    ok, why = may_autopilot(patch, s.get("autonomy", "review"))
    await emit(s, "ship", "patch", pr_url=pr_url, autopilot=ok, reason=why)
    await kg.learn_bug(s["repo"], s["diagnosis"], patch, s["failures"])       # self-improving memory
    await _register_patch(s, patch, pr_url)
    return {"pr_url": pr_url, "status": "passed" if ok else "awaiting_review"}


async def escalate(s: SwarmState) -> dict:
    await emit(s, "ship", "error", message="Could not produce a verified patch in 3 attempts; escalating to humans.")
    return {"status": "awaiting_review"}


async def learn_only(s: SwarmState) -> dict:
    kg = _kg()
    await kg.record_run(s)
    return {"status": "passed"}


async def _register_patch(s: SwarmState, patch: dict, pr_url: str | None) -> None:
    """Make the patch visible in the Incident & Self-Patch Review Console."""
    import os, httpx
    body = {"run_id": s["run_id"], "org_id": s["org_id"], "title": patch["title"], "root_cause": s["diagnosis"]["root_cause"],
            "diff": patch["diff"], "confidence": patch["confidence"], "verified_in_sandbox": bool(patch.get("verified")), "pr_url": pr_url}
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{os.getenv('TYPHOID_API', 'http://backend:8000')}/patches/internal", json=body,
                     headers={"Authorization": f"Bearer {os.getenv('TYPHOID_SERVICE_TOKEN', '')}"})
