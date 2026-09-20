from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    typhoid_env: str = "development"
    typhoid_secret_key: str = "change-me"
    typhoid_public_url: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://typhoid:typhoid@postgres:5432/typhoid"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60
    bus_backend: str = "redis"
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap: str = "kafka:9092"
    kafka_topic_runs: str = "typhoid.runs"
    kafka_topic_events: str = "typhoid.events"
    github_webhook_secret: str = ""
    gitlab_webhook_secret: str = ""
    autonomy_level: str = "review"  # observe | review | autopilot


@lru_cache
def get_settings() -> Settings:
    return Settings()
