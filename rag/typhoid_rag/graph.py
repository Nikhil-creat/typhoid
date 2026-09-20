"""Neo4j knowledge graph. Nodes: Repo, File, Test, Bug, Fix, Incident, Deploy.
Edges: (Test)-[:COVERS]->(File), (Bug)-[:LIVES_IN]->(File), (Fix)-[:RESOLVES]->(Bug),
       (Test)-[:FLAKY_WITH]->(Test), (Incident)-[:CAUSED_BY]->(Deploy)."""
import os
from neo4j import AsyncGraphDatabase


class KnowledgeGraph:
    def __init__(self):
        self.d = AsyncGraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
                                           auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")))

    async def _run(self, q: str, **p):
        async with self.d.session() as s:
            return [r.data() async for r in await s.run(q, **p)]

    async def hotspots(self, repo: str, ref: str) -> dict:
        incidents = await self._run(
            "MATCH (:Repo {name:$r})<-[:IN]-(f:File)<-[:LIVES_IN]-(b:Bug) "
            "WHERE b.created > datetime() - duration('P30D') RETURN f.path AS file, count(b) AS bugs ORDER BY bugs DESC LIMIT 10", r=repo)
        flaky = await self._run(
            "MATCH (t:Test {repo:$r}) WHERE t.flake_rate > 0.05 RETURN t.id AS id, t.flake_rate AS rate LIMIT 20", r=repo)
        return {"recent_incidents": incidents, "flaky_tests": flaky}

    async def record_bug(self, repo: str, dx: dict, patch: dict | None):
        await self._run(
            "MERGE (r:Repo {name:$repo}) CREATE (b:Bug {id:randomUUID(), cause:$cause, class:$cls, created:datetime()}) "
            "WITH r,b UNWIND $files AS p MERGE (f:File {path:p, repo:$repo}) MERGE (f)-[:IN]->(r) MERGE (b)-[:LIVES_IN]->(f)",
            repo=repo, cause=dx["root_cause"], cls=dx["class"], files=dx.get("suspect_files", []))
        if patch:
            await self._run("MATCH (b:Bug {cause:$c}) CREATE (:Fix {title:$t, diff:$d})-[:RESOLVES]->(b)",
                            c=dx["root_cause"], t=patch["title"], d=patch["diff"][:20000])

    async def blast_radius(self, repo: str, changed_files: list[str]) -> list[str]:
        """Which tests transitively cover the changed files? Powers change-based test selection."""
        rows = await self._run("MATCH (t:Test {repo:$r})-[:COVERS*1..2]->(f:File) WHERE f.path IN $fs RETURN DISTINCT t.id AS id",
                               r=repo, fs=changed_files)
        return [r["id"] for r in rows]
