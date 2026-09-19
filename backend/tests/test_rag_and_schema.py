import json

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import models
from app.rag import store
from app.tools.registry import call_tool


class FakeCollection:
    def __init__(self, distances):
        self.distances = distances

    def query(self, query_texts, n_results, where=None):
        n = len(self.distances)
        return {"documents": [[f"doc{i}" for i in range(n)]],
                "metadatas": [[{"source": "s", "title": "t"}] * n], "distances": [self.distances]}


def test_search_drops_passages_below_threshold(monkeypatch):
    monkeypatch.setattr(store, "get_collection", lambda: FakeCollection([0.4, 0.6, 0.85]))  # scores .6 .4 .15
    assert [h["score"] for h in store.search("q", min_score=0.30)] == [0.6, 0.4]


def test_search_docs_tool_says_so_when_nothing_is_relevant(db, monkeypatch):
    monkeypatch.setattr(store, "get_collection", lambda: FakeCollection([0.85, 0.9]))
    r = json.loads(call_tool(db, "search_docs", json.dumps({"query": "capital of France"})))
    assert r["passages"] == [] and "No sufficiently relevant" in r["note"]


def test_database_rejects_invalid_status(db):
    stack, check = db.query(models.Stack).first(), db.query(models.Check).first()
    db.add(models.CheckResult(stack_id=stack.id, check_id=check.id + 1000, status="banana", bucket="Strengths"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_database_rejects_negative_entity_count(db):
    stack, check = db.query(models.Stack).first(), db.query(models.Check).first()
    db.add(models.CheckResult(stack_id=stack.id, check_id=check.id, status="failed",
                              bucket="Actions Required", entity_count=-1))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_like_wildcards_from_the_model_are_treated_literally(db):
    r = json.loads(call_tool(db, "get_stack_summary", json.dumps({"stack_name": "%"})))
    assert "error" in r and "No stack matches" in r["error"]


def test_seed_refuses_to_overwrite_without_force():
    from scripts import seed
    with pytest.raises(SystemExit) as e:
        seed.main(force=False)
    assert "--force" in str(e.value)
