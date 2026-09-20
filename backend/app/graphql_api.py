import strawberry
from strawberry.fastapi import GraphQLRouter
from .store import store


@strawberry.type
class RunGQL:
    id: str
    status: str
    repo: str
    risk_score: float | None


@strawberry.type
class Query:
    @strawberry.field
    def runs(self, info, org_id: str = "demo") -> list[RunGQL]:
        return [RunGQL(id=r.id, status=r.status.value, repo=r.request.repo, risk_score=r.risk_score)
                for r in store.runs_for(org_id)]


graphql_router = GraphQLRouter(strawberry.Schema(Query), path="/graphql")
