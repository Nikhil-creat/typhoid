"""LangGraph supervisor: durable, checkpointed, resumable multi-agent workflow.

  risk_oracle → architect → synthetic_data → execution ─┐
                                                        ├→ chaos → (failures?) ─→ diagnose → write_patch → verify ─┬→ ship
                                                        │                                        ↑                 ├→ retry (≤3)
                                                        └→ learn_only  (all green)               └────────────────┘  └→ escalate
"""
from langgraph.graph import END, StateGraph
from . import agents as A
from .settings import settings
from .state import SwarmState


def _route_after_chaos(s: SwarmState) -> str:
    if s.get("killed"): return "end"
    return "diagnose" if s.get("failures") else "learn_only"


def build_graph(checkpointer=None):
    g = StateGraph(SwarmState)
    for name, fn in [("risk_oracle", A.risk_oracle), ("architect", A.architect), ("synthetic_data", A.synthetic_data),
                     ("execution", A.execution), ("chaos", A.chaos), ("diagnose", A.diagnose),
                     ("write_patch", A.write_patch), ("verify", A.verify_patch), ("ship", A.ship),
                     ("escalate", A.escalate), ("learn_only", A.learn_only)]:
        g.add_node(name, fn)
    g.set_entry_point("risk_oracle")
    g.add_edge("risk_oracle", "architect")
    g.add_edge("architect", "synthetic_data")
    g.add_edge("synthetic_data", "execution")
    g.add_edge("execution", "chaos")
    g.add_conditional_edges("chaos", _route_after_chaos, {"diagnose": "diagnose", "learn_only": "learn_only", "end": END})
    g.add_edge("diagnose", "write_patch")
    g.add_edge("write_patch", "verify")
    g.add_conditional_edges("verify", A.should_retry, {"ship": "ship", "retry": "write_patch", "escalate": "escalate"})
    for n in ("ship", "escalate", "learn_only"):
        g.add_edge(n, END)
    return g.compile(checkpointer=checkpointer)


async def make_checkpointer():
    dsn = settings().langgraph_checkpoint_dsn
    if not dsn:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    cm = AsyncPostgresSaver.from_conn_string(dsn)
    saver = await cm.__aenter__()
    await saver.setup()
    return saver
