"""Raw tool-calling loop against DeepSeek (OpenAI-compatible API). No framework on purpose."""
import json

from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.conversation import clean_history, conversation_notes
from app.db.models import Stack
from app.prompts import SYSTEM_PROMPT, refusal_message, scoped_system_prompt
from app.rag.reformulate import Completer, openai_completer
from app.rag.verify import verify_answer
from app.tools.registry import TOOL_SCHEMAS, scoped_tool_schemas
from app.tools.supervisor import ToolContext, supervised_call

MAX_STEPS = 6  # hard cap on LLM round-trips per question


def get_client() -> OpenAI:
    cfg = get_settings()
    if not cfg.deepseek_api_key:
        raise OpenAIError("DEEPSEEK_API_KEY is not set")
    return OpenAI(api_key=cfg.deepseek_api_key, base_url=cfg.deepseek_base_url,
                  timeout=cfg.llm_timeout_s, max_retries=1)


def _refusal_kind(arguments_json: str) -> str:
    try:
        kind = json.loads(arguments_json or "{}").get("kind")
    except (json.JSONDecodeError, AttributeError):
        kind = None
    return kind if kind in ("off_topic", "other_stack") else "off_topic"


def ask(db: Session, question: str, client: OpenAI | None = None, complete: Completer | None = None,
        stack: Stack | None = None, history: list[dict] | None = None) -> dict:
    """Answer one question. With `stack`, the chat is locked to that stack: the tools can only see it (enforced in
    supervised_call) and the prompt says so. With `history`, earlier turns are included so follow-ups resolve."""
    cfg = get_settings()
    client = client or get_client()
    complete = complete or openai_completer(client, cfg.llm_model)
    past = clean_history(history)
    ctx = ToolContext(db=db, question=question, complete=complete, stack=stack, conversation=conversation_notes(past))
    system = scoped_system_prompt(stack) if stack else SYSTEM_PROMPT
    tools = scoped_tool_schemas() if stack else TOOL_SCHEMAS
    messages = [{"role": "system", "content": system}, *past, {"role": "user", "content": question}]
    trace = []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=cfg.llm_model, messages=messages, tools=tools,
                                              max_tokens=cfg.llm_max_output_tokens)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            answer = msg.content or "I couldn't produce an answer. Please try rephrasing."
            return finish(ctx, answer, trace)

        messages.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            if tc.function.name == "out_of_scope":  # end the run with the fixed message; no second LLM call
                trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
                kind = _refusal_kind(tc.function.arguments)
                if kind == "other_stack" and stack is None:
                    kind = "off_topic"
                return finish(ctx, refusal_message(kind, stack), trace, verify=False, refusal=kind)
            result = supervised_call(ctx, tc.function.name, tc.function.arguments)
            trace.append({"name": tc.function.name, "arguments": tc.function.arguments})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return finish(ctx, "I couldn't finish answering within the tool-call limit.", trace, verify=False)


def finish(ctx: ToolContext, answer: str, trace: list[dict], verify: bool = True, off_topic: bool = False,
           refusal: str | None = None) -> dict:
    """Shared response shape for both agent implementations (optionally with the stretch citation check)."""
    verification = None
    if verify and get_settings().verify_answers and ctx.complete:
        verification = verify_answer(ctx.complete, answer, ctx.snippets)
    return {"answer": answer, "tool_calls": trace, "retries": ctx.events, "verification": verification,
            "off_topic": off_topic or refusal is not None, "refusal": refusal}
