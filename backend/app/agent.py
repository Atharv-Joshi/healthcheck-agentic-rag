"""Raw tool-calling loop against DeepSeek (OpenAI-compatible API). No framework on purpose."""
import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.tools.registry import TOOL_SCHEMAS, call_tool

load_dotenv()

MODEL = "deepseek-chat"  # not deepseek-reasoner: it doesn't support tool calling cleanly
MAX_STEPS = 6

SYSTEM_PROMPT = """You answer questions about a Contentstack Healthcheck audit report.
All report data in this system is synthetic mock data.

You have two kinds of tools; choose per question, and use both when a question needs both:
- Report tools (list_stacks, get_stack_summary, get_check_status, list_checks_by_status,
  list_actions_required, get_failed_entities, list_checks): the source of truth for numbers, statuses,
  names and lists about a specific stack. Never guess or estimate these.
- search_docs: Contentstack documentation for conceptual questions (why it matters, how to fix it,
  best practices). Base explanations on the returned passages and mention the source page title;
  if nothing relevant is returned, say so instead of improvising.
Example of using both: "why does the SSO check matter for Globex?" -> get_check_status, then search_docs.

If the user doesn't name a stack and more than one exists, call list_stacks and ask which they mean.
For general questions unrelated to the report, answer briefly without tools. Be concise and cite the
numbers you retrieved."""


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                  base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))


def ask(db: Session, question: str, client: OpenAI | None = None) -> dict:
    client = client or get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace = []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content, "tool_calls": trace}

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            result = call_tool(db, tc.function.name, tc.function.arguments)
            trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return {"answer": "I couldn't finish answering within the tool-call limit.", "tool_calls": trace}
