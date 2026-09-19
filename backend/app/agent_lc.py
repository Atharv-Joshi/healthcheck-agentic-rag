"""LangChain version of the agent (same tools, prompt and return shape as agent.py).

What the framework replaces from the raw loop in agent.py:
  - the while-loop + message bookkeeping        -> create_agent (a LangGraph state graph)
  - appending tool results with tool_call_id    -> ToolNode
  - MAX_STEPS                                   -> recursion_limit
  - the OpenAI client                           -> ChatOpenAI
"""
import json
import os

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.errors import GraphRecursionError
from sqlalchemy.orm import Session

from app.agent import MAX_STEPS, MODEL, SYSTEM_PROMPT
from app.tools.registry import TOOL_SCHEMAS, call_tool


def build_tools(db: Session) -> list[StructuredTool]:
    """Wrap the existing OpenAI-format schemas + dispatcher, so both agents share one tool definition."""
    tools = []
    for spec in TOOL_SCHEMAS:
        fn = spec["function"]

        def run(_name=fn["name"], **kwargs) -> str:
            return call_tool(db, _name, json.dumps(kwargs))

        tools.append(StructuredTool.from_function(
            func=run, name=fn["name"], description=fn["description"], args_schema=fn["parameters"]))
    return tools


def get_model() -> ChatOpenAI:
    return ChatOpenAI(model=MODEL, api_key=os.environ["DEEPSEEK_API_KEY"],
                      base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))


def ask(db: Session, question: str, model=None) -> dict:
    agent = create_agent(model or get_model(), build_tools(db), system_prompt=SYSTEM_PROMPT)
    # each step is one model node + one tools node, hence the factor of 2
    config = {"recursion_limit": 2 * MAX_STEPS + 1}
    try:
        state = agent.invoke({"messages": [HumanMessage(question)]}, config)
    except GraphRecursionError:
        return {"answer": "I couldn't finish answering within the tool-call limit.", "tool_calls": []}

    messages = state["messages"]
    trace = [{"name": c["name"], "arguments": json.dumps(c["args"])}
             for m in messages if isinstance(m, AIMessage) for c in m.tool_calls]
    return {"answer": messages[-1].content, "tool_calls": trace}
