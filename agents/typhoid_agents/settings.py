from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class S(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model_reasoning: str = "claude-sonnet-5"
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"
    vlm_model: str = "claude-sonnet-5"
    llm_monthly_budget_usd: float = 500
    llm_max_tokens: int = 4096
    bus_backend: str = "redis"
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap: str = "kafka:9092"
    kafka_topic_runs: str = "typhoid.runs"
    kafka_topic_events: str = "typhoid.events"
    langgraph_checkpoint_dsn: str = ""
    worker_image: str = "typhoid/runner:latest"
    worker_cpu_limit: float = 1.0
    worker_mem_limit: str = "1g"
    worker_ttl_seconds: int = 900
    chaos_max_blast_radius: float = 0.3
    chaos_allow_production: bool = False
    vault_addr: str = "http://vault:8200"
    vault_token: str = ""
    autopilot_min_confidence: float = 0.92
    autopilot_max_diff_lines: int = 60
    github_app_id: str = ""
    github_app_private_key_path: str = ""


@lru_cache
def settings() -> S:
    return S()
