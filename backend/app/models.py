"""Pydantic contracts shared across the gateway, event bus and agent swarm."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    queued = "queued"
    planning = "planning"
    running = "running"
    chaos = "chaos"
    diagnosing = "diagnosing"
    patching = "patching"
    awaiting_review = "awaiting_review"
    passed = "passed"
    failed = "failed"


class ChaosSpec(BaseModel):
    """A steady-state hypothesis experiment, not random breakage."""
    hypothesis: str = "p95 latency stays < 800ms and checkout succeeds"
    faults: list[Literal["latency", "packet_loss", "cpu_throttle", "db_outage", "dns_failure"]] = ["latency"]
    intensity: float = Field(0.2, ge=0, le=1)   # capped by CHAOS_MAX_BLAST_RADIUS server-side
    duration_s: int = Field(60, ge=5, le=900)


class RunRequest(BaseModel):
    repo: str
    ref: str = "main"
    target_url: str
    user_story: str | None = None           # natural-language test intent
    mockup_b64: str | None = None            # uploaded UI mockup for visual-first tests
    chaos: ChaosSpec | None = None
    autonomy: Literal["observe", "review", "autopilot"] | None = None


class Run(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    org_id: str
    request: RunRequest
    status: RunStatus = RunStatus.queued
    created_at: datetime = Field(default_factory=_now)
    risk_score: float | None = None          # predicted regression risk 0..1


class AgentEvent(BaseModel):
    """Everything the swarm does is streamed as an event (thought, tool call, result)."""
    run_id: str
    org_id: str
    agent: str
    kind: Literal["status", "thought", "tool", "result", "visual_diff", "chaos", "patch", "error"]
    payload: dict[str, Any] = {}
    ts: datetime = Field(default_factory=_now)


class PatchProposal(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    run_id: str
    org_id: str
    title: str
    root_cause: str
    diff: str
    confidence: float
    verified_in_sandbox: bool = False        # patch was re-run against failing tests
    pr_url: str | None = None
    state: Literal["proposed", "approved", "rejected", "merged"] = "proposed"
