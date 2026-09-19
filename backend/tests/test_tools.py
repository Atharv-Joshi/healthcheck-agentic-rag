import json

from app.tools import queries
from app.tools.registry import TOOL_SCHEMAS, call_tool


def run(db, name, **args):
    return json.loads(call_tool(db, name, json.dumps(args)))


def test_schemas_and_dispatch_table_match():
    from app.tools.registry import _DISPATCH
    assert {s["function"]["name"] for s in TOOL_SCHEMAS} == set(_DISPATCH)


def test_stack_summary_counts_add_up(db):
    r = run(db, "get_stack_summary", stack_name="globex")
    assert r["stack"] == "Globex Corporate Site"
    assert sum(r["checks_by_status"].values()) == 24


def test_ambiguous_stack_returns_candidates(db):
    r = run(db, "get_stack_summary", stack_name="acme")
    assert "ambiguous" in r["error"] and "Acme Retail - Web" in r["error"]


def test_unknown_stack_lists_known_stacks(db):
    assert "Known stacks" in run(db, "get_stack_summary", stack_name="nope")["error"]


def test_actions_required_sorted_and_limited(db):
    r = run(db, "list_actions_required", stack_name="Acme Retail - Web", limit=3)
    counts = [x["affected_entities"] for x in r["results"]]
    assert len(counts) <= 3 and counts == sorted(counts, reverse=True)
    assert all(x["bucket"] == "Actions Required" for x in r["results"])


def test_negative_limit_is_clamped_not_sliced_from_the_end(db):
    r = run(db, "list_checks_by_status", stack_name="globex", limit=-3)
    assert r["returned"] == 1 and len(r["results"]) == 1


def test_limit_is_capped(db):
    r = run(db, "list_checks_by_status", stack_name="globex", limit=10_000)
    assert len(r["results"]) <= queries.MAX_LIMIT


def test_negative_offset_does_not_crash(db):
    r = run(db, "get_failed_entities", stack_name="globex", check_name="unused assets", offset=-5)
    assert "entities" in r


def test_failed_entities_pagination(db):
    a = run(db, "get_failed_entities", stack_name="globex", check_name="unused assets", limit=2, offset=0)
    b = run(db, "get_failed_entities", stack_name="globex", check_name="unused assets", limit=2, offset=2)
    assert a["entities"] and a["entities"] != b["entities"]


def test_bad_argument_name_is_reported_to_the_model(db):
    assert "Bad arguments" in run(db, "list_stacks", bogus=1)["error"]


def test_malformed_json_arguments(db):
    assert "Bad arguments" in json.loads(call_tool(db, "get_stack_summary", "{not json"))["error"]


def test_unexpected_exception_is_contained_and_session_recovers(db, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("db exploded")
    monkeypatch.setitem(__import__("app.tools.registry", fromlist=["_DISPATCH"])._DISPATCH, "list_stacks", boom)
    assert run(db, "list_stacks")["error"] == "Internal error while running this tool."
