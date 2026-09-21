"""Raw tool-calling loop against DeepSeek (OpenAI-compatible API). No framework on purpose."""
from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.prompts import OFF_TOPIC_MESSAGE, SYSTEM_PROMPT
from app.rag.reformulate import Completer, openai_completer
from app.rag.verify import verify_answer
from app.tools.registry import TOOL_SCHEMAS
from app.tools.supervisor import ToolContext, supervised_call

MAX_STEPS = 6  # hard cap on LLM round-trips per question


def get_client() -> OpenAI:
    cfg = get_settings()
    if not cfg.deepseek_api_key:
        raise OpenAIError("DEEPSEEK_API_KEY is not set")
    return OpenAI(api_key=cfg.deepseek_api_key, base_url=cfg.deepseek_base_url,
                  timeout=cfg.llm_timeout_s, max_retries=1)


def ask(db: Session, question: str, client: OpenAI | None = None, complete: Completer | None = None) -> dict:
    cfg = get_settings()
    client = client or get_client()
    complete = complete or openai_completer(client, cfg.llm_model)
    ctx = ToolContext(db=db, question=question, complete=complete)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace = []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=cfg.llm_model, messages=messages, tools=TOOL_SCHEMAS,
                                              max_tokens=cfg.llm_max_output_tokens)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            answer = msg.content or "I couldn't produce an answer. Please try rephrasing."
            return finish(ctx, answer, trace)

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            if tc.function.name == "out_of_scope":  # end the run with the fixed message; no second LLM call
                trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
                return finish(ctx, OFF_TOPIC_MESSAGE, trace, verify=False, off_topic=True)
            result = supervised_call(ctx, tc.function.name, tc.function.arguments)
            trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return finish(ctx, "I couldn't finish answering within the tool-call limit.", trace, verify=False)


def finish(ctx: ToolContext, answer: str, trace: list[dict], verify: bool = True, off_topic: bool = False) -> dict:
    """Shared response shape for both agent implementations (optionally with the stretch citation check)."""
    verification = None
    if verify and get_settings().verify_answers and ctx.complete:
        verification = verify_answer(ctx.complete, answer, ctx.snippets)
    return {"answer": answer, "tool_calls": trace, "retries": ctx.events, "verification": verification,
            "off_topic": off_topic}
