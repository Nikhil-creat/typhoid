"""Provider-agnostic LLM client with a cost governor and structured-JSON helper."""
import json, re
from anthropic import AsyncAnthropic
from .settings import settings

# USD per 1M tokens (in, out). Keep in sync with provider pricing; used only for budgeting.
PRICE = {"reasoning": (3.0, 15.0), "fast": (1.0, 5.0)}


class BudgetExceeded(RuntimeError): ...


class CostGovernor:
    def __init__(self): self.spent = 0.0
    def charge(self, tier: str, tin: int, tout: int):
        pin, pout = PRICE[tier]
        self.spent += tin / 1e6 * pin + tout / 1e6 * pout
        if self.spent > settings().llm_monthly_budget_usd:
            raise BudgetExceeded(f"LLM budget hit: ${self.spent:.2f}")


governor = CostGovernor()
_client: AsyncAnthropic | None = None


def _c() -> AsyncAnthropic:
    global _client
    _client = _client or AsyncAnthropic(api_key=settings().anthropic_api_key)
    return _client


async def ask(system: str, user: str, *, tier: str = "reasoning", images: list[str] | None = None) -> str:
    s = settings()
    model = s.anthropic_model_reasoning if tier == "reasoning" else s.anthropic_model_fast
    content: list[dict] = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b}}
                           for b in (images or [])]
    content.append({"type": "text", "text": user})
    r = await _c().messages.create(model=model, max_tokens=s.llm_max_tokens, system=system,
                                   messages=[{"role": "user", "content": content}])
    governor.charge(tier, r.usage.input_tokens, r.usage.output_tokens)
    return "".join(b.text for b in r.content if b.type == "text")


async def ask_json(system: str, user: str, **kw) -> dict:
    raw = await ask(system + "\nReturn ONLY valid JSON. No prose, no markdown fences.", user, **kw)
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    return json.loads(raw)
