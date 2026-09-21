"""LangChain version of the agent (same tools, prompt, limits and return shape as agent.py).

What the framework replaces from the raw loop in agent.py:
  - the while-loop + message bookkeeping        -> create_agent (a LangGraph state graph)
  - appending tool results with tool_call_id    -> ToolNode
  - MAX_STEPS                                   -> recursion_limit
  - the OpenAI client                           -> ChatOpenAI
"""
import json
import logging

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from sqlalchemy.orm import Session

from app.agent import MAX_STEPS, finish
from app.config import get_settings
from app.prompts import OFF_TOPIC_MESSAGE, SYSTEM_PROMPT
from app.rag.reformulate import Completer, openai_completer
from app.tools.registry import TOOL_SCHEMAS
from app.tools.supervisor import ToolContext, supervised_call

log = logging.getLogger(__name__)

FALLBACK_ANSWER = "I couldn't produce an answer. Please try rephrasing."


def build_tools(ctx: ToolContext) -> list[StructuredTool]:
    """Wrap the existing OpenAI-format schemas + supervised dispatcher: both agents share tools AND retrieval
    supervision (reformulation, one-shot retry), so they differ only in orchestration."""
    tools = []
    for spec in TOOL_SCHEMAS:
        fn = spec["function"]

        def run(_name=fn["name"], **kwargs) -> str:
            return supervised_call(ctx, _name, json.dumps(kwargs))

        tools.append(StructuredTool.from_function(
            func=run, name=fn["name"], description=fn["description"], args_schema=fn["parameters"],
            # declining ends the run right after the tool: no further model call that could drift into answering
            return_direct=fn["name"] == "out_of_scope"))
    return tools


def get_model() -> ChatOpenAI:
    cfg = get_settings()
    if not cfg.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")
    return ChatOpenAI(model=cfg.llm_model, api_key=cfg.deepseek_api_key, base_url=cfg.deepseek_base_url,
                      timeout=cfg.llm_timeout_s, max_retries=1, max_tokens=cfg.llm_max_output_tokens)


def _text(content) -> str:
    """Message content may be a string or a list of content blocks; return the plain text either way."""
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content or [])


def ask(db: Session, question: str, model=None, complete: Completer | None = None) -> dict:
    cfg = get_settings()
    if complete is None and model is None:  # real run: reformulation shares the configured provider
        from app.agent import get_client
        complete = openai_completer(get_client(), cfg.llm_model)
    ctx = ToolContext(db=db, question=question, complete=complete)
    agent = create_agent(model or get_model(), build_tools(ctx), system_prompt=SYSTEM_PROMPT)
    # each step is one model node + one tools node, hence the factor of 2
    config = {"recursion_limit": 2 * MAX_STEPS + 1}
    try:
        state = agent.invoke({"messages": [HumanMessage(question)]}, config)
    except GraphRecursionError:
        log.warning("step limit reached for question=%r", question)
        return finish(ctx, "I couldn\'t finish answering within the tool-call limit.", [], verify=False)

    messages = state["messages"]
    trace = [{"name": c["name"], "arguments": json.dumps(c["args"])}
             for m in messages if isinstance(m, AIMessage) for c in m.tool_calls]
    if any(t["name"] == "out_of_scope" for t in trace):  # same fixed refusal as the raw agent
        return finish(ctx, OFF_TOPIC_MESSAGE, trace, verify=False, off_topic=True)
    return finish(ctx, _text(messages[-1].content).strip() or FALLBACK_ANSWER, trace)
