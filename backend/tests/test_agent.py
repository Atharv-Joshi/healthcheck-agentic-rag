"""Agent loop tests with a stubbed LLM client (no network, no cost)."""
from types import SimpleNamespace as NS

from app.agent import MAX_STEPS, ask
from app.config import get_settings


class Msg(NS):
    def model_dump(self, **_):
        return {"role": "assistant", "content": self.content, "tool_calls": [
            {"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}}
            for t in self.tool_calls or []]}


def tool_call(name, args, id="c1"):
    return NS(id=id, function=NS(name=name, arguments=args))


def client(script):
    """script: list of assistant messages, returned in order (last one repeats)."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        m = script[min(len(seen) - 1, len(script) - 1)]
        return NS(choices=[NS(message=m)])

    return NS(chat=NS(completions=NS(create=create))), seen


def test_tool_then_answer(db):
    c, seen = client([Msg(content=None, tool_calls=[tool_call("get_stack_summary", '{"stack_name":"globex"}')]),
                      Msg(content="Globex: 9 failed.", tool_calls=None)])
    r = ask(db, "How is Globex?", c)
    assert r["answer"] == "Globex: 9 failed."
    assert [t["name"] for t in r["tool_calls"]] == ["get_stack_summary"]
    assert seen[1]["messages"][-1]["role"] == "tool"  # tool result was fed back
    assert "Globex Corporate Site" in seen[1]["messages"][-1]["content"]


def test_no_tools_needed(db):
    c, _ = client([Msg(content="Paris.", tool_calls=None)])
    r = ask(db, "Capital of France?", c)
    assert (r["answer"], r["tool_calls"], r["retries"], r["verification"]) == ("Paris.", [], [], None)


def test_empty_model_content_gets_a_fallback_not_none(db):
    c, _ = client([Msg(content=None, tool_calls=None)])
    assert isinstance(ask(db, "hi", c)["answer"], str) and ask(db, "hi", c)["answer"]


def test_step_limit_stops_a_looping_model(db):
    looping = Msg(content=None, tool_calls=[tool_call("list_stacks", "{}")])
    c, seen = client([looping])
    r = ask(db, "loop forever", c)
    assert len(seen) == MAX_STEPS and "limit" in r["answer"]


def test_tool_error_is_fed_back_and_loop_continues(db):
    c, seen = client([Msg(content=None, tool_calls=[tool_call("get_stack_summary", '{"stack_name":"nope"}')]),
                      Msg(content="Which stack did you mean?", tool_calls=None)])
    r = ask(db, "status?", c)
    assert "Known stacks" in seen[1]["messages"][-1]["content"]
    assert r["answer"] == "Which stack did you mean?"


# ---- agentic retrieval, end to end through the loop ----
def _docs_run(monkeypatch, distances_by_query, completions):
    from app.rag import store
    from tests.test_supervisor import FakeCollection, completer
    monkeypatch.setattr(store, "get_collection", lambda: FakeCollection(distances_by_query))
    return completer(*completions)


def test_weak_search_is_retried_and_reported_in_the_response(db, monkeypatch):
    complete = _docs_run(monkeypatch, {"weak q": [0.7], "better q": [0.3]}, ["weak q", "better q"])
    c, seen = client([Msg(content=None, tool_calls=[tool_call("search_docs", '{"query": "why care"}')]),
                      Msg(content="Because of X.", tool_calls=None)])
    r = ask(db, "why should I care?", c, complete=complete)
    assert [e["kind"] for e in r["retries"]] == ["vector_retry"] and r["answer"] == "Because of X."
    fed_back = seen[1]["messages"][-1]["content"]
    assert '"retried": true' in fed_back and '"confidence": "high"' in fed_back


def test_thin_evidence_reaches_the_model_with_a_do_not_guess_instruction(db, monkeypatch):
    complete = _docs_run(monkeypatch, {}, ["a", "b"])  # everything scores 0.05 -> filtered
    c, seen = client([Msg(content=None, tool_calls=[tool_call("search_docs", '{"query": "zzz"}')]),
                      Msg(content="I couldn't find that in the docs.", tool_calls=None)])
    ask(db, "zzz?", c, complete=complete)
    assert "Do NOT answer from general knowledge" in seen[1]["messages"][-1]["content"]


def test_unsupported_answer_is_flagged_when_verification_is_on(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "verify_answers", True)
    complete = _docs_run(monkeypatch, {"q": [0.3]}, ["q", "no\nThe docs never say that."])
    c, _ = client([Msg(content=None, tool_calls=[tool_call("search_docs", '{"query": "q"}')]),
                   Msg(content="A confident but unsupported claim.", tool_calls=None)])
    r = ask(db, "q?", c, complete=complete)
    assert r["verification"]["status"] == "unsupported"


def test_verification_is_off_by_default(db, monkeypatch):
    complete = _docs_run(monkeypatch, {"q": [0.3]}, ["q"])
    c, _ = client([Msg(content=None, tool_calls=[tool_call("search_docs", '{"query": "q"}')]),
                   Msg(content="Answer.", tool_calls=None)])
    assert ask(db, "q?", c, complete=complete)["verification"] is None


# ---- scope guard: off-topic questions get a fixed refusal ----
def test_out_of_scope_tool_ends_the_run_with_the_fixed_message_and_no_second_llm_call(db):
    from app.prompts import OFF_TOPIC_MESSAGE
    c, seen = client([Msg(content=None, tool_calls=[tool_call("out_of_scope", '{"reason": "history"}')]),
                      Msg(content="World War 2 was...", tool_calls=None)])  # must never be reached
    r = ask(db, "What is ww2", c)
    assert r["answer"] == OFF_TOPIC_MESSAGE and r["off_topic"] is True
    assert [t["name"] for t in r["tool_calls"]] == ["out_of_scope"]
    assert len(seen) == 1  # the model's own answer is never requested, so it can't leak an off-topic reply


def test_in_scope_answers_are_not_flagged_off_topic(db):
    c, _ = client([Msg(content="Hello!", tool_calls=None)])
    assert ask(db, "hi", c)["off_topic"] is False


def test_out_of_scope_wins_even_if_the_model_also_asks_for_data(db):
    c, _ = client([Msg(content=None, tool_calls=[tool_call("list_stacks", "{}", id="a"),
                                                  tool_call("out_of_scope", "{}", id="b")]),
                   Msg(content="x", tool_calls=None)])
    assert ask(db, "mixed", c)["off_topic"] is True
