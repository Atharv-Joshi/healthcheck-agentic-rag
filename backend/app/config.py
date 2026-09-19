"""Central, typed configuration. Real environment variables override the project-root .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ROOT.parent / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://localhost:5432/healthcheck_qa"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"  # not deepseek-reasoner: no clean tool calling
    llm_timeout_s: float = 30
    llm_max_output_tokens: int = 800

    rate_limit: str = "10/minute"
    log_level: str = "INFO"

    chroma_dir: Path = _ROOT / "chroma_db"
    frontend_dist: Path = Path("/app/frontend_dist")
    # Measured on this corpus: on-topic queries score >= 0.43, off-topic <= 0.18 (cosine similarity).
    min_doc_score: float = 0.30


@lru_cache
def get_settings() -> Settings:
    return Settings()
