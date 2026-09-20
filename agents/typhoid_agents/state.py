from __future__ import annotations
from operator import add
from typing import Annotated, Any, TypedDict


class Failure(TypedDict):
    test_id: str
    error: str
    trace: str
    screenshot_path: str | None


class SwarmState(TypedDict, total=False):
    # inputs
    run_id: str
    org_id: str
    repo: str
    ref: str
    target_url: str
    user_story: str | None
    mockup_b64: str | None
    chaos: dict | None
    autonomy: str                      # observe | review | autopilot

    # planning
    risk_score: float
    plan: list[dict]                   # test tree from Architect
    personas: list[dict]               # Synthetic Data agent output

    # execution
    results: Annotated[list[dict], add]
    failures: list[Failure]
    visual_findings: Annotated[list[dict], add]
    chaos_findings: Annotated[list[dict], add]

    # remediation (reflexion loop)
    diagnosis: dict[str, Any]
    patch: dict[str, Any] | None
    patch_attempts: int
    verified: bool
    pr_url: str | None
    status: str
    killed: bool
