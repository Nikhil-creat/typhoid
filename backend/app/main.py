import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import issue_token
from .config import get_settings
from .graphql_api import graphql_router
from .routers import incidents, runs, studio, webhooks
from . import ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(ws.ingest_events())
    yield
    task.cancel()


app = FastAPI(title="TYPHOID Gateway", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[get_settings().typhoid_public_url],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
for r in (runs.router, incidents.router, studio.router, webhooks.router, ws.router):
    app.include_router(r)
app.include_router(graphql_router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/dev/token", include_in_schema=False)
async def dev_token(org: str = "demo", role: str = "admin"):
    """Development only. Replace with OIDC in production."""
    if get_settings().typhoid_env != "development":
        return {"error": "disabled"}
    return {"token": issue_token("dev", org, role)}
