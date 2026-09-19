"""Same behaviours as test_agent.py, for the LangChain implementation (fake chat model, no network)."""
import itertools

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage

from app import main
from app.agent_lc import FALLBACK_ANSWER, _text, ask, build_tools
from app.tools.registry import TOOL_SCHEMAS


class FakeModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):  # create_agent binds tools; the fake ignores them
        return self


def call(name, args, id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id}])


def test_wraps_every_shared_tool_with_its_schema(db):
    tools = build_tools(db)
    assert [t.name for t in tools] == [s["function"]["name"] for s in TOOL_SCHEMAS]
    status = next(t for t in tools if t.name == "list_checks_by_status")
    assert status.args["status"]["enum"] == ["passed", "failed", "skipped"]


def test_tool_then_answer(db):
    r = ask(db, "How is Globex?", FakeModel(messages=iter([
        call("get_stack_summary", {"stack_name": "globex"}), AIMessage(content="Globex: 9 failed.")])))
    assert r["answer"] == "Globex: 9 failed."
    assert [t["name"] for t in r["tool_calls"]] == ["get_stack_summary"]


def test_no_tools_needed(db):
    assert ask(db, "Capital of France?", FakeModel(messages=iter([AIMessage(content="Paris.")]))) == \
        {"answer": "Paris.", "tool_calls": []}


def test_empty_model_content_gets_a_fallback(db):
    assert ask(db, "hi", FakeModel(messages=iter([AIMessage(content="")])))["answer"] == FALLBACK_ANSWER


def test_content_blocks_are_flattened_to_text():
    assert _text([{"type": "text", "text": "Hello "}, {"type": "text", "text": "world"}]) == "Hello world"
    assert _text(None) == ""


def test_step_limit_stops_a_looping_model(db):
    # fresh message objects each turn, like a real model (LangGraph de-duplicates messages by id)
    looping = (call("list_stacks", {}, id=f"c{i}") for i in itertools.count())
    r = ask(db, "loop", FakeModel(messages=looping))
    assert "limit" in r["answer"]


def test_tool_error_reaches_the_model_and_loop_continues(db):
    seen = []

    class Spy(FakeModel):
        def _generate(self, messages, *a, **k):
            seen.append(messages)
            return super()._generate(messages, *a, **k)

    r = ask(db, "status?", Spy(messages=iter([
        call("get_stack_summary", {"stack_name": "nope"}), AIMessage(content="Which stack did you mean?")])))
    tool_msgs = [m for m in seen[-1] if isinstance(m, ToolMessage)]
    assert "Known stacks" in tool_msgs[0].content
    assert r["answer"] == "Which stack did you mean?"


def test_agent_impl_setting_selects_the_langchain_agent(monkeypatch):
    monkeypatch.setattr(main.settings, "agent_impl", "langchain")
    assert main._select_agent() is ask
    monkeypatch.setattr(main.settings, "agent_impl", "raw")
    assert main._select_agent() is main.ask_raw
