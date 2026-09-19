"""Agent loop tests with a stubbed LLM client (no network, no cost)."""
from types import SimpleNamespace as NS

from app.agent import MAX_STEPS, ask


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
    assert ask(db, "Capital of France?", c) == {"answer": "Paris.", "tool_calls": []}


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
