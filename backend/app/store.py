"""Thin persistence layer. In-memory for the blueprint; swap for SQLAlchemy models in prod
(schema: runs, events, patches, orgs, projects — every row carries org_id)."""
from collections import defaultdict
from .models import Run, PatchProposal, AgentEvent


class Store:
    def __init__(self):
        self.runs: dict[str, Run] = {}
        self.patches: dict[str, PatchProposal] = {}
        self.events: dict[str, list[AgentEvent]] = defaultdict(list)

    def runs_for(self, org: str) -> list[Run]:
        return sorted((r for r in self.runs.values() if r.org_id == org), key=lambda r: r.created_at, reverse=True)

    def patches_for(self, org: str) -> list[PatchProposal]:
        return [p for p in self.patches.values() if p.org_id == org]


store = Store()
