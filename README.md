# TYPHOID
Autonomous testing, chaos engineering and self-healing CI/CD. A swarm of AI agents plans tests, breaks your app on purpose, judges what it sees, writes the fix, **proves the fix in a fresh sandbox**, then opens the pull request.

## Live 3D demo (GitHub Pages)
The `site/` folder is a static, fully 3D experience (Three.js): a petri dish holding the nine agents, an event bus, a growing knowledge graph, chaos sandboxes that shake under fault injection, a CNN visual-diff panel, and a patch that turns green when verified. Drive it from the Test Studio and watch the reflexion loop, autonomy gates and kill-switch work.

1. Push this repo to GitHub (branch `main`).
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. The `deploy-pages` workflow tests the simulation engine, then publishes `site/`.
4. Open `https://<your-username>.github.io/<repo-name>/`.

Pages only serves static files, so the hosted demo runs the **same agent graph and guardrail rules as a simulation in your browser** (`site/js/sim.js`, unit-tested with `node --test`). The real FastAPI/Kafka/LangGraph stack runs with `docker compose` or Helm; point a real dashboard at it once you host the backend.

## Data flow
```
Next.js dashboard ──REST/GraphQL/WS──▶ FastAPI gateway ──▶ Kafka / Redis Streams ──▶ Swarm workers (LangGraph, checkpointed in Postgres)
     ▲                                     ▲ webhooks (GitHub/GitLab/Jira)                │
     └──────────── live AgentEvents ◀──────┴────────────────────────────────────────────┤
                                                                                        ├─▶ Qdrant + Neo4j (hybrid RAG, self-learning)
                                                                                        ├─▶ VLM + CNN visual / WCAG engine
                                                                                        └─▶ Ephemeral Docker/K8s chaos sandboxes ◀─ Vault dynamic creds
```
Graph: `risk_oracle → architect → synthetic_data → execution → chaos → (green: learn) | (red: diagnose → write_patch → verify ⟲×3 → ship | escalate)`

## Run it
```bash
make runner                      # build the sandbox image
cp .env.example .env             # add ANTHROPIC_API_KEY (+ GitHub App creds for PRs)
docker compose up --build        # UI :3000  API :8000/docs  Neo4j :7474  Qdrant :6333
make kafka                       # optional: Kafka instead of Redis Streams (BUS_BACKEND=kafka)
helm install typhoid infra/helm/typhoid -n typhoid --create-namespace   # production
```

## Agentic + futuristic features built in
| Feature | Where |
|---|---|
| Multi-agent swarm with a durable, resumable supervisor (survives crashes) | `agents/graph.py` |
| **Reflexion loop**: patches are applied and re-tested in a clean sandbox, retried up to 3x with the failure output as feedback | `agents.py: write_patch/verify` |
| **Predictive risk oracle**: scores a change from graph history and sets test depth | `risk_oracle`, `rag/graph.py` |
| **Self-improving memory**: every fixed bug is embedded (Qdrant) and linked (Neo4j) for the next run | `rag/hybrid.py` |
| Steady-state-hypothesis chaos, injected **mid-test**, always healed | `workers/chaos/manager.py` |
| CNN heatmap + VLM verdict ("does this change matter?") + mockup conformance | `agents/vision/` |
| Agentic exploratory crawler + keyboard-trap probe + axe WCAG 2.2 | `vision/crawler.py`, `a11y.py` |
| **Autonomy dial**: observe / review / autopilot, with hard gates (verified, confidence ≥ 0.92, diff ≤ 60 lines, no protected paths) | `guardrails.py` |
| Prompt-injection isolation: page content, logs and issues are wrapped as untrusted data | `guardrails.py` |
| LLM cost governor with a monthly hard cap | `llm.py` |
| Kill-switch, pause/resume/steer from the UI over WebSocket | `ws.py`, `worker.py` |
| **MCP server**: other AI agents/IDEs can start runs and read patches as tools | `agents/mcp_server.py` |
| KEDA autoscaling on bus lag, default-deny NetworkPolicy, read-only rootfs, cap-drop ALL | `infra/helm` |
| Dogfooding: TYPHOID tests its own PRs | `.github/workflows/ci.yml` |

## Honest status
This is a production-shaped **blueprint**, not a tested release. Before real use:
- Replace the in-memory `backend/app/store.py` with SQLAlchemy models (schema noted in the file) and OIDC login (`/dev/token` is dev-only).
- The runner speaks a constrained JSON step DSL that the Architect must emit; add schema validation for plans.
- Vendor `axe.min.js` into `agents/typhoid_agents/vision/`; provide Vault database/OAuth engines matching `infra/vault/typhoid-worker.hcl`.
- The K8s worker runtime (`WORKER_RUNTIME=k8s`, Jobs instead of `docker.sock`) is wired in RBAC/Helm but the manager currently implements Docker; mounting `docker.sock` is for local dev only.
- Run chaos against staging, never production (blocked by default). Autopilot merges should stay off until you trust the verifier on your codebase.
- Install shadcn components with `npx shadcn@latest add button card dialog` as you extend the UI.

## Author

**★NIKHIL CHARY SRIRAMOJU★**
BTech CSE (Final Year)

- GitHub: [Nikhil-creat](https://github.com/Nikhil-creat)
- LinkedIn: [nikhil-chary-sriramoju](https://in.linkedin.com/in/nikhil-chary-sriramoju-95041b38a)
- Email: sriramojunikhil66@gmail.com
- Instagram: [@nikhil__sriramoju](https://www.instagram.com/nikhil__sriramoju)
- Facebook: [Profile](https://www.facebook.com/profile.php?id=100079201124141)

  
