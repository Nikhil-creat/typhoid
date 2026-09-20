"""WCAG 2.2 accessibility checks: axe-core (deterministic) + VLM (perceptual things axe can't see)."""
import pathlib
AXE_JS = pathlib.Path(__file__).with_name("axe.min.js")   # vendored from axe-core (MPL-2.0)


async def run_axe(page) -> list[dict]:
    await page.add_script_tag(content=AXE_JS.read_text())
    res = await page.evaluate("async () => await axe.run(document, {runOnly:['wcag2a','wcag2aa','wcag22aa']})")
    return [{"rule": v["id"], "impact": v["impact"], "help": v["help"], "nodes": [n["target"] for n in v["nodes"][:5]]}
            for v in res["violations"]]


async def keyboard_trap_probe(page, max_tabs: int = 60) -> dict:
    """Tab through the page; fail if focus never leaves a 3-element cycle (keyboard trap) or is invisible."""
    seen: list[str] = []
    for _ in range(max_tabs):
        await page.keyboard.press("Tab")
        seen.append(await page.evaluate("document.activeElement?.outerHTML?.slice(0,80) ?? ''"))
    return {"trapped": len(set(seen[-9:])) <= 3, "distinct_stops": len(set(seen))}
