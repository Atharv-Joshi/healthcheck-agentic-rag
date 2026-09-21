from app.config import Settings


def test_env_file_points_at_the_project_root_dotenv():
    """Regression: it once pointed at the *parent* of the project root, so a local .env was never loaded."""
    env_file = Settings.model_config["env_file"]
    assert env_file.name == ".env"
    assert (env_file.parent / "backend" / "app" / "config.py").is_file()
    assert (env_file.parent / ".env.example").is_file()


def test_real_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    assert Settings().llm_model == "some-other-model"


import pytest


@pytest.mark.parametrize("given, expected", [
    ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),         # Heroku/older Render style
    ("postgresql://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),                 # Render/Railway style
    ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),        # already correct: untouched
    ("postgresql://u:p%40x@host/db?sslmode=require", "postgresql+psycopg2://u:p%40x@host/db?sslmode=require"),
])
def test_database_url_is_normalized_to_the_installed_driver(given, expected):
    assert Settings(database_url=given).database_url == expected


def test_normalized_urls_are_accepted_by_sqlalchemy():
    """The point of the normalizer: `postgres://` makes SQLAlchemy 2 raise NoSuchModuleError."""
    from sqlalchemy import create_engine
    create_engine(Settings(database_url="postgres://u:p@localhost/db").database_url)  # no connect, just parse+load driver
    with pytest.raises(Exception):
        create_engine("postgres://u:p@localhost/db")
