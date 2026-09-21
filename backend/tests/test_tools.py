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


def test_out_of_scope_is_a_registered_tool(db):
    assert "out_of_scope" in {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert run(db, "out_of_scope", reason="history")["off_topic"] is True


def test_scoped_schemas_drop_stack_name_and_list_stacks_but_keep_everything_else():
    from app.tools.registry import STACK_TOOLS, scoped_tool_schemas
    scoped = {s["function"]["name"]: s for s in scoped_tool_schemas()}
    assert "list_stacks" not in scoped and {"search_docs", "out_of_scope", "get_check_status"} <= set(scoped)
    for name in STACK_TOOLS - {"list_stacks"}:
        params = scoped[name]["function"]["parameters"]
        assert "stack_name" not in params["properties"] and "stack_name" not in params.get("required", [])
    assert "stack_name" in next(s for s in TOOL_SCHEMAS if s["function"]["name"] == "get_check_status")[
        "function"]["parameters"]["properties"]  # the shared unscoped schema was not mutated


def test_an_exact_stack_name_wins_even_when_it_is_a_prefix_of_another(db):
    from datetime import date
    from app.db.models import Stack
    db.add(Stack(name="Acme", entries_count=1, assets_count=1, run_date=date(2026, 9, 1)))
    db.flush()
    try:
        assert queries._resolve_stack(db, "Acme").name == "Acme"
        # a genuinely ambiguous partial name is still reported as ambiguous, with candidates
        assert "ambiguous" in run(db, "get_stack_summary", stack_name="Acme R")["error"]
    finally:
        db.rollback()
