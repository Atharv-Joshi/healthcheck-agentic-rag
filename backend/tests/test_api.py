import openai
import pytest
from fastapi.testclient import TestClient

import app.main as main


@pytest.fixture()
def client(monkeypatch):
    main.limiter.reset()
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ask_returns_answer(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": f"echo {q}", "tool_calls": []})
    assert client.post("/api/ask", json={"question": "hi"}).json()["answer"] == "echo hi"


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": "x" * 1001}])
def test_ask_validates_input(client, body):
    assert client.post("/api/ask", json=body).status_code == 422


def test_provider_error_becomes_502_not_500(client, monkeypatch):
    def fail(db, q):
        raise openai.APIConnectionError(request=None)
    monkeypatch.setattr(main, "ask", fail)
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 502


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": "ok", "tool_calls": []})
    codes = [client.post("/api/ask", json={"question": "hi"}).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and 429 in codes[10:]


def test_ui_mounted_at_root_does_not_shadow_the_api(tmp_path, monkeypatch):
    """Regression: the built UI is a static mount at '/', which only allows GET. The browser posts to /api/ask,
    which must still reach the API route (it used to 405 in production because the API lived at /ask)."""
    from fastapi import FastAPI
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler

    (tmp_path / "index.html").write_text("<html>ui</html>")
    prod = FastAPI()
    prod.state.limiter = main.limiter
    prod.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    prod.include_router(main.api)
    main.mount_frontend(prod, tmp_path)  # mounted last, exactly as in main.py
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": "ok", "tool_calls": []})
    main.limiter.reset()

    c = TestClient(prod)
    assert c.get("/").text == "<html>ui</html>"                       # the UI is served
    assert c.post("/api/ask", json={"question": "hi"}).status_code == 200  # and the API still works
    assert c.post("/ask", json={"question": "hi"}).status_code == 405     # unprefixed path is the static mount's


def test_health_stays_at_the_root_for_platform_health_checks(client):
    assert client.get("/health").status_code == 200


def test_off_topic_flag_is_returned_to_the_client(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": "declined", "tool_calls": [], "off_topic": True})
    body = client.post("/api/ask", json={"question": "what is ww2"}).json()
    assert body["off_topic"] is True and body["answer"] == "declined"


def test_off_topic_defaults_to_false(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": "ok", "tool_calls": []})
    assert client.post("/api/ask", json={"question": "hi"}).json()["off_topic"] is False
