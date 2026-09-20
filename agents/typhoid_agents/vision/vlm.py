"""VLM judge: the CNN says *where* something changed, the VLM says *whether it matters* and *why*."""
import base64
from ..llm import ask_json
from ..guardrails import wrap_untrusted

SYSTEM = """You are a senior UI QA engineer. You get a baseline screenshot, a candidate screenshot and CNN-flagged
regions. Decide if the change is an intentional design update, a regression, or noise. Check: overlap/clipping,
layout shift, truncated text, broken images, contrast, tap-target size, missing focus states, responsive breakage."""


async def judge(baseline: bytes, candidate: bytes, regions: list[dict], viewport: str) -> dict:
    return await ask_json(
        SYSTEM,
        f"Viewport: {viewport}\nCNN regions (normalised): {regions[:20]}\n"
        'Schema: {"verdict":"regression|intentional|noise","severity":"low|med|high","summary":str,"issues":[{"type":str,"where":str}]}',
        images=[base64.b64encode(baseline).decode(), base64.b64encode(candidate).decode()],
    )


async def mockup_conformance(mockup_b64: str, screenshot: bytes) -> dict:
    """Visual-first testing: does the built page match the designer's mockup?"""
    return await ask_json(
        "Compare a design mockup (image 1) with the implemented page (image 2). List concrete deviations.",
        'Schema: {"match_score":float,"deviations":[{"element":str,"expected":str,"actual":str}]}',
        images=[mockup_b64, base64.b64encode(screenshot).decode()],
    )
