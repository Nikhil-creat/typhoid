"""Hybrid retrieval = vector similarity (what *looks* like this bug) + graph expansion (what is *connected* to it)."""
from .graph import KnowledgeGraph
from .vector import VectorStore


class HybridKnowledge:
    def __init__(self):
        self.vec, self.kg = VectorStore(), KnowledgeGraph()

    async def recall(self, query: str, k: int = 5) -> list[dict]:
        return await self.vec.search(query, k)

    async def hotspots(self, repo: str, ref: str) -> dict:
        return await self.kg.hotspots(repo, ref)

    async def learn_bug(self, repo: str, dx: dict, patch: dict | None, failures: list[dict]):
        """Self-improving loop: every fixed bug becomes retrievable context for the next run."""
        await self.kg.record_bug(repo, dx, patch)
        text = f"{dx['root_cause']}\n" + "\n".join(f["error"][:300] for f in failures[:3])
        await self.vec.upsert(text, {"repo": repo, "class": dx["class"], "fix": (patch or {}).get("title", "")})

    async def record_run(self, state: dict):
        await self.vec.upsert(f"clean run of {state['repo']}: {len(state.get('results', []))} tests passed",
                              {"repo": state["repo"], "class": "clean"})
