"""Retrieval supervision: the 'agentic' part of agentic RAG.

Sits between the agent loop and the tools. For every tool call it:
  1. reformulates doc-search queries into clean, self-contained ones (rag/reformulate.py),
  2. judges whether the retrieval was thin (empty / too short / low similarity / zero DB rows),
  3. if so, retries EXACTLY ONCE (one retry per tool call, so it can't loop),
  4. tells the model how much to trust what it got, and records/logs every retry.

Retry strategy depends on the path that came back thin:
  - docs search thin      -> re-search with a differently-worded query (and no category filter)
  - DB returned zero rows -> fall back to docs search (background only; never presented as report data)
There is deliberately no docs->DB fallback: the check descriptions and recommendations in Postgres are already
embedded in the vector index, so a catalog lookup would only return what the vector search already covers.

Both agent implementations (raw loop and LangChain) call `supervised_call`, so behaviour is defined once.
"""
import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import get_settings
from app.rag import store
from app.rag.reformulate import Completer, broaden_query, reformulate_query
from app.db.models import Stack
from app.tools.registry import STACK_TOOLS, call_tool

log = logging.getLogger(__name__)

INSUFFICIENT = ("Retrieval was weak. Do NOT answer from general knowledge or guess: tell the user you could not "
                "find enough information in the report or documentation, and say what you did find (if anything).")
DB_EMPTY_NOTE = ("The database returned no matching rows. State that plainly. Any 'fallback_docs' are background "
                 "documentation only, NOT report data; never present them as findings from this report.")


@dataclass
class ToolContext:
    """Per-question state shared by every tool call in one agent run."""
    db: Session
    question: str
    complete: Completer | None = None           # LLM for reformulation; None disables it
    notes: list[str] = field(default_factory=list)      # short summaries of earlier report lookups
    events: list[dict] = field(default_factory=list)    # retries triggered this run (returned to the client)
    snippets: list[str] = field(default_factory=list)   # doc passages the answer may rely on (for verification)
    stack: Stack | None = None                          # when set, the chat is locked to this one stack
    conversation: list[str] = field(default_factory=list)  # earlier-turn context lines for the query reformulator

    def context(self) -> list[str]:
        """What the reformulator sees: what was said earlier, plus the report lookups made this turn."""
        return self.conversation[-3:] + self.notes[-3:]


# ---------- judging retrieval quality ----------

def doc_weakness(passages: list[dict]) -> str | None:
    """Why a docs result is thin, or None if it is good enough to answer from."""
    cfg = get_settings()
    if not passages:
        return "no passages above the relevance threshold"
    top = max(p["score"] for p in passages)
    if top < cfg.retry_score:
        return f"low confidence (top similarity {top:.2f} < {cfg.retry_score})"
    if sum(len(p["text"]) for p in passages) < cfg.min_evidence_chars:
        return f"too little evidence (< {cfg.min_evidence_chars} chars)"
    return None


def db_is_empty(tool: str, data: dict) -> bool:
    """Zero-row results. A check that simply passed has no failed entities, which is not 'thin'."""
    if tool == "list_stacks":
        return not data.get("stacks")
    if tool == "list_checks":
        return not data.get("checks")
    if tool in ("list_checks_by_status", "list_actions_required"):
        return data.get("total_matching") == 0
    if tool == "get_failed_entities":
        return not data.get("entities") and data.get("status") == "failed"
    return False


def _strength(passages: list[dict]) -> tuple[float, int]:
    return (max((p["score"] for p in passages), default=0.0), sum(len(p["text"]) for p in passages))


# ---------- supervised execution ----------

def _record(ctx: ToolContext, event: dict) -> None:
    ctx.events.append(event)
    log.warning("RETRY triggered tool=%s kind=%s reason=%s outcome=%s", event["tool"], event["kind"],
                event["reason"], event["outcome"])


def _search_docs(ctx: ToolContext, args: dict) -> dict:
    cfg = get_settings()
    draft, category = args.get("query") or ctx.question, args.get("category")
    query = draft
    if cfg.reformulate_queries and ctx.complete:
        query = reformulate_query(ctx.complete, ctx.question, draft, ctx.context())
    passages = store.search(query, k=4, category=category)
    info = {"query": query, **({"original_query": draft} if query != draft else {})}

    weakness = doc_weakness(passages)
    if weakness:  # one retry: differently-worded query, category filter dropped
        retry_q = broaden_query(ctx.complete, ctx.question, query, ctx.context()) if ctx.complete else query
        retried = store.search(retry_q, k=4)
        improved = _strength(retried) > _strength(passages)
        if improved:
            passages, info["query"] = retried, retry_q
        info["retried"] = True
        _record(ctx, {"tool": "search_docs", "kind": "vector_retry", "reason": weakness, "first_query": query,
                      "retry_query": retry_q, "outcome": "improved" if improved else "no better"})

    remaining = doc_weakness(passages)
    info["confidence"] = "none" if not passages else "low" if remaining else "high"
    if remaining:
        info["instruction"] = INSUFFICIENT
    ctx.snippets.extend(p["text"] for p in passages)
    return {"passages": passages, "retrieval": info}


def _db_fallback(ctx: ToolContext, tool: str, data: dict) -> dict:
    cfg = get_settings()
    query = ctx.question
    if cfg.reformulate_queries and ctx.complete:
        query = reformulate_query(ctx.complete, ctx.question, ctx.question, ctx.context())
    passages = store.search(query, k=3)
    _record(ctx, {"tool": tool, "kind": "db_fallback", "reason": "database returned zero rows",
                  "retry_query": query, "outcome": f"{len(passages)} background passages"})
    ctx.snippets.extend(p["text"] for p in passages)
    data["fallback_docs"] = passages
    data["retrieval"] = {"confidence": "none", "retried": True, "instruction": DB_EMPTY_NOTE}
    return data


def supervised_call(ctx: ToolContext, name: str, arguments_json: str) -> str:
    """Run one tool call under supervision and return the JSON string for the model."""
    if ctx.stack is not None:  # stack lock: enforced here, so nothing the model or user says can reach another stack
        if name == "list_stacks":
            return json.dumps({"error": "Not available: this chat is locked to one stack."})
        if name in STACK_TOOLS:
            try:
                args = json.loads(arguments_json or "{}")
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Bad arguments: {e}"})
            args["stack_name"] = ctx.stack.name  # overrides anything the model supplied
            arguments_json = json.dumps(args)
    if name == "search_docs":
        try:
            return json.dumps(_search_docs(ctx, json.loads(arguments_json or "{}")))
        except Exception:
            ctx.db.rollback()
            log.exception("supervised search_docs failed")
            return json.dumps({"error": "Documentation search failed."})

    raw = call_tool(ctx.db, name, arguments_json)
    try:
        data = json.loads(raw)
        if "error" not in data and db_is_empty(name, data):
            raw = json.dumps(_db_fallback(ctx, name, data))
    except Exception:
        log.exception("db fallback failed for tool=%s", name)
    ctx.notes.append(f"{name}({arguments_json}) -> {raw[:160]}")
    return raw
