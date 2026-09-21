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
