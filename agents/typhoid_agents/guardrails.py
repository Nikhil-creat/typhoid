"""Safety rails around an autonomous system that can write code and break things.

Principles:  least privilege · bounded blast radius · human-in-the-loop by default ·
             untrusted-input isolation · everything auditable.
"""
import re
from .settings import settings

SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{36}", r"sk-[A-Za-z0-9]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
]
INJECTION_HINTS = re.compile(r"ignore (all|previous) instructions|system prompt|exfiltrate|curl .*\|\s*sh", re.I)
PROTECTED_PATHS = (".github/workflows/", "infra/", "Dockerfile", ".env", "secrets", "deploy")


def scrub(text: str) -> str:
    for p in SECRET_PATTERNS:
        text = re.sub(p, "[REDACTED]", text)
    return text


def wrap_untrusted(label: str, text: str) -> str:
    """Page content / logs / issue bodies are DATA, never instructions."""
    flag = " (contains suspected prompt-injection)" if INJECTION_HINTS.search(text) else ""
    return f"<untrusted source='{label}'{flag}>\n{scrub(text)[:20000]}\n</untrusted>"


def clamp_chaos(spec: dict, target_is_prod: bool) -> dict:
    s = settings()
    if target_is_prod and not s.chaos_allow_production:
        raise PermissionError("Chaos against production is disabled by policy")
    spec = dict(spec)
    spec["intensity"] = min(float(spec.get("intensity", 0.2)), s.chaos_max_blast_radius)
    spec["duration_s"] = min(int(spec.get("duration_s", 60)), 900)
    return spec


def diff_touches_protected(diff: str) -> bool:
    return any(p in line for line in diff.splitlines() if line.startswith(("+++", "---")) for p in PROTECTED_PATHS)


def may_autopilot(patch: dict, autonomy: str) -> tuple[bool, str]:
    """Auto-merge only when EVERY gate passes; otherwise a human decides."""
    s = settings()
    lines = sum(1 for l in patch["diff"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    if autonomy != "autopilot":                       return False, "autonomy level is not autopilot"
    if not patch.get("verified"):                      return False, "patch not verified in sandbox"
    if patch["confidence"] < s.autopilot_min_confidence: return False, "confidence below threshold"
    if lines > s.autopilot_max_diff_lines:             return False, "diff too large"
    if diff_touches_protected(patch["diff"]):          return False, "touches protected paths"
    return True, "all gates passed"
