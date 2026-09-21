"""Central, typed configuration. Real environment variables override the project-root .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://localhost:5432/healthcheck_qa"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"  # not deepseek-reasoner: no clean tool calling
    llm_timeout_s: float = 30
    llm_max_output_tokens: int = 800

    agent_impl: str = "raw"  # raw | langchain
    rate_limit: str = "10/minute"
    log_level: str = "INFO"

    chroma_dir: Path = _ROOT / "chroma_db"
    frontend_dist: Path = Path("/app/frontend_dist")
    # --- agentic retrieval supervision ---
    reformulate_queries: bool = True   # rewrite the doc-search query before embedding it
    retry_score: float = 0.40          # top similarity below this => "low confidence" => one retry
    min_evidence_chars: int = 200      # less passage text than this => "too thin" => one retry
    verify_answers: bool = False       # stretch: LLM check that retrieved snippets support the answer (+1 call)
    # Measured on this corpus: on-topic queries score >= 0.43, off-topic <= 0.18 (cosine similarity).
    min_doc_score: float = 0.30

    @field_validator("database_url")
    @classmethod
    def _use_psycopg2_driver(cls, url: str) -> str:
        """Hosts (Render, Railway, Heroku) hand out `postgres://` or `postgresql://` URLs. SQLAlchemy 2 rejects the
        first outright and the second only works by default-driver accident, so pin the driver we install."""
        for scheme in ("postgres://", "postgresql://"):
            if url.startswith(scheme):
                return "postgresql+psycopg2://" + url[len(scheme):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
