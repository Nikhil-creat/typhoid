from typhoid_agents.guardrails import clamp_chaos, may_autopilot, scrub, diff_touches_protected
import pytest

def test_scrub_redacts_keys():
    assert "AKIA" not in scrub("key=AKIAABCDEFGHIJKLMNOP")

def test_chaos_intensity_is_clamped():
    assert clamp_chaos({"intensity": 0.9}, False)["intensity"] <= 0.3

def test_chaos_blocks_prod():
    with pytest.raises(PermissionError):
        clamp_chaos({}, True)

def test_autopilot_requires_all_gates():
    p = {"diff": "--- a/x.py\n+++ b/x.py\n+1", "confidence": 0.99, "verified": True}
    assert may_autopilot(p, "autopilot")[0]
    assert not may_autopilot({**p, "verified": False}, "autopilot")[0]
    assert not may_autopilot(p, "review")[0]

def test_protected_paths():
    assert diff_touches_protected("--- a/.github/workflows/ci.yml\n+++ b/.github/workflows/ci.yml")
