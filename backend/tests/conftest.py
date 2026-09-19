"""Tests run against a separate, freshly seeded Postgres database (never the dev data)."""
import os

import psycopg2
import pytest
from sqlalchemy.engine import make_url

TEST_DB = "healthcheck_qa_test"
_base = os.getenv("TEST_DATABASE_URL") or os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://localhost:5432/healthcheck_qa")
_url = make_url(_base).set(database=TEST_DB)
os.environ["DATABASE_URL"] = _url.render_as_string(hide_password=False)  # before app.db is imported
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")


def _ensure_test_db() -> None:
    conn = psycopg2.connect(host=_url.host, port=_url.port, user=_url.username,
                            password=_url.password, dbname="postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    _ensure_test_db()
    from scripts import seed
    seed.main()


@pytest.fixture()
def db():
    from app.db.database import SessionLocal
    with SessionLocal() as session:
        yield session
