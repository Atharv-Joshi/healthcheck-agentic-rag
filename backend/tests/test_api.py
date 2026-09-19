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
    assert client.post("/ask", json={"question": "hi"}).json()["answer"] == "echo hi"


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": "x" * 1001}])
def test_ask_validates_input(client, body):
    assert client.post("/ask", json=body).status_code == 422


def test_provider_error_becomes_502_not_500(client, monkeypatch):
    def fail(db, q):
        raise openai.APIConnectionError(request=None)
    monkeypatch.setattr(main, "ask", fail)
    assert client.post("/ask", json={"question": "hi"}).status_code == 502


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(main, "ask", lambda db, q: {"answer": "ok", "tool_calls": []})
    codes = [client.post("/ask", json={"question": "hi"}).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and 429 in codes[10:]
