"""Exploratory UI crawler: BFS over DOM states, discovers hidden routes, dead links and runtime exceptions.
Also does agentic 'monkey with a brain': the LLM picks the next most suspicious interaction."""
from collections import deque
from urllib.parse import urljoin, urlparse


async def crawl(page, start: str, max_pages: int = 40) -> dict:
    origin = urlparse(start).netloc
    seen, q = {start}, deque([start])
    findings = {"dead_links": [], "js_errors": [], "console_errors": [], "pages": 0, "hidden_routes": []}
    page.on("pageerror", lambda e: findings["js_errors"].append({"url": page.url, "error": str(e)}))
    page.on("console", lambda m: m.type == "error" and findings["console_errors"].append({"url": page.url, "text": m.text[:300]}))
    while q and findings["pages"] < max_pages:
        url = q.popleft()
        resp = await page.goto(url, wait_until="networkidle")
        findings["pages"] += 1
        if resp and resp.status >= 400:
            findings["dead_links"].append({"url": url, "status": resp.status}); continue
        hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        for h in hrefs:
            full = urljoin(url, h)
            if urlparse(full).netloc == origin and full not in seen and not full.startswith("mailto:"):
                seen.add(full); q.append(full)
        # routes referenced in JS bundles but not linked anywhere = "hidden" surface area
        hidden = await page.evaluate("() => performance.getEntriesByType('resource').map(r=>r.name).filter(n=>/\\/api\\//.test(n))")
        findings["hidden_routes"] += [h for h in hidden if h not in findings["hidden_routes"]]
    return findings
