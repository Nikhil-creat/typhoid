"""Expose TYPHOID as an MCP server so ANY agent (Claude, IDE copilots, other swarms) can call it as a tool:
   'run a chaos test on staging', 'what regressed in the last deploy?', 'explain this incident'."""
import httpx, os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("typhoid")
API = os.getenv("TYPHOID_API", "http://backend:8000")
HDR = {"Authorization": f"Bearer {os.getenv('TYPHOID_MCP_TOKEN', '')}"}


@mcp.tool()
async def start_test_run(repo: str, target_url: str, user_story: str = "", chaos: bool = False) -> dict:
    """Start an autonomous test run (optionally with chaos experiments)."""
    body = {"repo": repo, "target_url": target_url, "user_story": user_story or None,
            "chaos": {"faults": ["latency"], "intensity": 0.2} if chaos else None}
    async with httpx.AsyncClient() as c:
        return (await c.post(f"{API}/runs", json=body, headers=HDR)).json()


@mcp.tool()
async def list_open_patches() -> list:
    """List AI-proposed patches awaiting human review."""
    async with httpx.AsyncClient() as c:
        return (await c.get(f"{API}/patches", headers=HDR)).json()


if __name__ == "__main__":
    mcp.run()
