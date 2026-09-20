"""Runs INSIDE the sandbox. Drives Playwright, API checks, visual + a11y engines. Prints one JSON line."""
import asyncio, json, os, subprocess, sys, time
from playwright.async_api import async_playwright

TARGET = os.environ["TARGET_URL"]


async def run_step(page, step: dict) -> dict:
    t0 = time.perf_counter()
    try:
        # Steps are compiled by the Architect into a constrained DSL, never arbitrary code.
        for act in step.get("actions", [{"op": "goto", "url": TARGET}]):
            op = act["op"]
            if op == "goto":   await page.goto(act.get("url", TARGET), wait_until="networkidle")
            elif op == "click": await page.click(act["selector"])
            elif op == "fill":  await page.fill(act["selector"], act["value"])
            elif op == "expect_text": await page.wait_for_selector(f"text={act['text']}", timeout=5000)
            elif op == "expect_status":
                r = await page.request.get(act["url"]); assert r.status == act["status"], f"status {r.status}"
        return {"test_id": step["id"], "passed": True, "ms": (time.perf_counter() - t0) * 1000}
    except Exception as e:
        path = f"/tmp/{step['id']}.png"
        await page.screenshot(path=path)
        return {"test_id": step["id"], "passed": False, "error": str(e)[:500], "trace": repr(e)[:2000],
                "screenshot_path": path, "ms": (time.perf_counter() - t0) * 1000}


async def run_plan(plan, personas, timeout=300, **_):
    results, visual = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):      # desktop + mobile
            ctx = await b.new_context(viewport=vp)
            page = await ctx.new_page()
            for step in sorted(plan, key=lambda s: s.get("priority", 5)):
                if step["kind"] in {"e2e", "api", "explore"}:
                    results.append(await run_step(page, step))
            await page.goto(TARGET)
            visual.append({"viewport": f"{vp['width']}x{vp['height']}", "png_path": f"/tmp/vp{vp['width']}.png"})
            await page.screenshot(path=visual[-1]["png_path"], full_page=True)
            await ctx.close()
        await b.close()
    ms = sorted(r["ms"] for r in results) or [0]
    return {"results": results, "visual": visual, "p95_ms": ms[int(len(ms) * 0.95) - 1 if len(ms) > 1 else 0]}


async def apply_and_retest(diff, ids, regression_test, **_):
    subprocess.run(["git", "clone", "--depth", "1", "--branch", os.environ["REF"], f"https://github.com/{os.environ['REPO']}.git", "/tmp/repo"], check=True)
    ap = subprocess.run(["git", "apply", "-"], input=diff.encode(), cwd="/tmp/repo", capture_output=True)
    if ap.returncode: return {"all_passed": False, "output": ap.stderr.decode()}
    t = subprocess.run(["sh", "-c", "npm ci && npm test --silent || pytest -q"], cwd="/tmp/repo", capture_output=True, timeout=600)
    return {"all_passed": t.returncode == 0, "output": (t.stdout + t.stderr).decode()[-4000:]}


if __name__ == "__main__":
    op, payload = sys.argv[1], json.loads(sys.argv[2])
    print(json.dumps(asyncio.run(globals()[op](**payload))))
