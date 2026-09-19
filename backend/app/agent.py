"""Raw tool-calling loop against DeepSeek (OpenAI-compatible API). No framework on purpose."""
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.prompts import SYSTEM_PROMPT
from app.tools.registry import TOOL_SCHEMAS, call_tool

MAX_STEPS = 6  # hard cap on LLM round-trips per question


def get_client() -> OpenAI:
    cfg = get_settings()
    if not cfg.deepseek_api_key:
        raise OpenAIError("DEEPSEEK_API_KEY is not set")
    return OpenAI(api_key=cfg.deepseek_api_key, base_url=cfg.deepseek_base_url,
                  timeout=cfg.llm_timeout_s, max_retries=1)


def ask(db: Session, question: str, client: OpenAI | None = None) -> dict:
    cfg = get_settings()
    client = client or get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace = []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=cfg.llm_model, messages=messages, tools=TOOL_SCHEMAS,
                                              max_tokens=cfg.llm_max_output_tokens)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content or "I couldn't produce an answer. Please try rephrasing.", "tool_calls": trace}

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            result = call_tool(db, tc.function.name, tc.function.arguments)
            trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return {"answer": "I couldn't finish answering within the tool-call limit.", "tool_calls": trace}
