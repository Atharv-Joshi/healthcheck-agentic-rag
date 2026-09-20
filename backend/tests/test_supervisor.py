"""Agentic behaviours: reformulation, one-shot retry on thin results, DB->docs fallback, citation check."""
import json
import logging
from types import SimpleNamespace as NS

import pytest

from app.rag import store
from app.rag.verify import verify_answer
from app.tools.supervisor import ToolContext, db_is_empty, doc_weakness, supervised_call

LONG = "x" * 300  # enough text to clear the min-evidence rule


class FakeCollection:
    """query text -> list of cosine *distances* (score = 1 - distance); records every query and where-filter."""

    def __init__(self, by_query, default=None):
        self.by_query, self.default, self.seen = by_query, default or [0.95], []

    def query(self, query_texts, n_results, where=None):
        q = query_texts[0]
        self.seen.append((q, where))
        d = self.by_query.get(q, self.default)
        return {"documents": [[LONG] * len(d)], "metadatas": [[{"source": "s", "title": "t"}] * len(d)],
                "distances": [d]}


def completer(*replies):
    it, calls = iter(replies), []

    def complete(system, user):
        calls.append(user)
        return next(it)
    complete.calls = calls
    return complete


def search(ctx, **args):
    return json.loads(supervised_call(ctx, "search_docs", json.dumps(args)))


@pytest.fixture()
def ctx(db):
    return ToolContext(db=db, question="why should I care about this one?", notes=["get_check_status -> SSO Enabled"])


# ---- judging ----
def test_doc_weakness_rules():
    ok = [{"text": LONG, "score": 0.6}]
    assert doc_weakness(ok) is None
    assert "no passages" in doc_weakness([])
    assert "low confidence" in doc_weakness([{"text": LONG, "score": 0.35}])
    assert "too little evidence" in doc_weakness([{"text": "short", "score": 0.9}])


def test_db_is_empty_rules():
    assert db_is_empty("list_checks_by_status", {"total_matching": 0, "results": []})
    assert not db_is_empty("list_checks_by_status", {"total_matching": 3})
    assert db_is_empty("get_failed_entities", {"entities": [], "status": "failed"})
    assert not db_is_empty("get_failed_entities", {"entities": [], "status": "passed"})  # passing check: legit
    assert not db_is_empty("get_stack_summary", {})


# ---- reformulation ----
def test_query_is_reformulated_before_searching(ctx, monkeypatch):
    col = FakeCollection({"SSO business impact": [0.3]})
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer("SSO business impact")
    r = search(ctx, query="this one")
    assert col.seen[0][0] == "SSO business impact"
    assert r["retrieval"]["original_query"] == "this one" and r["retrieval"]["confidence"] == "high"
    assert "SSO Enabled" in ctx.complete.calls[0]  # earlier report lookups were given as context


def test_reformulation_can_be_disabled(ctx, monkeypatch):
    monkeypatch.setattr("app.tools.supervisor.get_settings", lambda: NS(
        reformulate_queries=False, retry_score=0.4, min_evidence_chars=200))
    col = FakeCollection({"raw q": [0.3]})
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer()  # would raise StopIteration if called
    search(ctx, query="raw q")
    assert col.seen[0][0] == "raw q"


# ---- retry on thin docs results ----
def test_good_results_do_not_retry(ctx, monkeypatch):
    monkeypatch.setattr(store, "get_collection", lambda: FakeCollection({"q": [0.3]}))
    ctx.complete = completer("q")
    search(ctx, query="q")
    assert ctx.events == [] and len(ctx.complete.calls) == 1


def test_low_confidence_triggers_exactly_one_retry_that_can_improve(ctx, monkeypatch, caplog):
    col = FakeCollection({"weak q": [0.7], "better q": [0.3]})  # scores .30 (thin) vs .70 (good)
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer("weak q", "better q")
    with caplog.at_level(logging.WARNING):
        r = search(ctx, query="x", category="Security")
    assert [q for q, _ in col.seen] == ["weak q", "better q"]
    assert col.seen[0][1] == {"category": "Security"} and col.seen[1][1] is None  # filter dropped on retry
    assert r["retrieval"]["retried"] and r["retrieval"]["confidence"] == "high"
    assert r["retrieval"]["query"] == "better q"
    assert ctx.events[0]["kind"] == "vector_retry" and ctx.events[0]["outcome"] == "improved"
    assert "RETRY triggered" in caplog.text


def test_still_thin_after_retry_tells_the_model_not_to_answer(ctx, monkeypatch):
    col = FakeCollection({}, default=[0.9])  # every query scores 0.10 -> filtered out entirely
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer("first", "second")
    r = search(ctx, query="unanswerable")
    assert len(col.seen) == 2  # capped at ONE retry, no loop
    assert r["passages"] == [] and r["retrieval"]["confidence"] == "none"
    assert "Do NOT answer" in r["retrieval"]["instruction"]
    assert ctx.events[0]["outcome"] == "no better"


def test_retry_keeps_the_better_of_the_two_results(ctx, monkeypatch):
    col = FakeCollection({"first": [0.62], "second": [0.8]})  # .38 (thin, kept) vs .20 (filtered)
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer("first", "second")
    r = search(ctx, query="q")
    assert r["retrieval"]["query"] == "first" and r["retrieval"]["confidence"] == "low"


# ---- DB empty -> docs fallback ----
def test_empty_db_result_falls_back_to_docs_once(ctx, monkeypatch):
    col = FakeCollection({}, default=[0.3])
    monkeypatch.setattr(store, "get_collection", lambda: col)
    ctx.complete = completer("background query")
    r = json.loads(supervised_call(ctx, "list_checks_by_status", json.dumps(
        {"stack_name": "globex", "status": "failed", "category": "Nonexistent"})))
    assert r["total_matching"] == 0 and r["fallback_docs"]
    assert "NOT report data" in r["retrieval"]["instruction"]
    assert [e["kind"] for e in ctx.events] == ["db_fallback"] and len(col.seen) == 1


def test_non_empty_db_result_is_untouched(ctx, monkeypatch):
    monkeypatch.setattr(store, "get_collection", lambda: pytest.fail("docs must not be searched"))
    r = json.loads(supervised_call(ctx, "get_stack_summary", '{"stack_name": "globex"}'))
    assert "fallback_docs" not in r and ctx.events == []


def test_db_errors_are_not_treated_as_empty(ctx, monkeypatch):
    monkeypatch.setattr(store, "get_collection", lambda: pytest.fail("docs must not be searched"))
    assert "error" in json.loads(supervised_call(ctx, "get_stack_summary", '{"stack_name": "nope"}'))


def test_notes_accumulate_for_later_reformulation(ctx):
    supervised_call(ctx, "get_stack_summary", '{"stack_name": "globex"}')
    assert "Globex" in ctx.notes[-1]


# ---- stretch: citation check ----
def test_verify_supported_and_unsupported():
    yes = verify_answer(lambda s, u: "yes\nMatches the snippet.", "answer", ["snippet"])
    no = verify_answer(lambda s, u: "No\nThe snippet never mentions that.", "answer", ["snippet"])
    assert yes["status"] == "supported" and no["status"] == "unsupported"


def test_verify_skips_when_no_docs_were_used_and_fails_open():
    assert verify_answer(lambda s, u: "no", "a", [])["status"] == "skipped"

    def boom(s, u):
        raise TimeoutError()
    assert verify_answer(boom, "a", ["s"])["status"] == "skipped"
