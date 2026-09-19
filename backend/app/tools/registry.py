"""OpenAI-format tool schemas plus dispatch. The descriptions are what the LLM routes on."""
import json
import logging
import time

from sqlalchemy.orm import Session

from app.rag import store

from . import queries
from .queries import EntityNotFound

log = logging.getLogger(__name__)

_STACK = {"type": "string", "description": "Stack name or unambiguous part of it, e.g. 'Globex'."}


def _fn(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}}


TOOL_SCHEMAS = [
    _fn("list_stacks", "List all audited stacks with entry/asset counts and run date. Use when the stack is unclear.", {}, []),
    _fn("list_checks", "List the names of all health checks, optionally for one category.",
        {"category": {"type": "string", "description": "Security, Content Modeling, Content, or Other Configurations"}}, []),
    _fn("get_stack_summary", "Overall counts of checks by status and bucket for a stack. Use for 'how healthy is X' questions.",
        {"stack_name": _STACK}, ["stack_name"]),
    _fn("get_check_status", "Status, affected-entity count, description and recommendation for ONE check on a stack.",
        {"stack_name": _STACK, "check_name": {"type": "string", "description": "Check name or part of it."}},
        ["stack_name", "check_name"]),
    _fn("list_checks_by_status", "Filter a stack's check results by status, bucket, and/or category, sorted by most affected entities. Use for counts and lists.",
        {"stack_name": _STACK,
         "status": {"type": "string", "enum": ["passed", "failed", "skipped"]},
         "bucket": {"type": "string", "enum": ["Actions Required", "Areas of Opportunity", "Strengths"]},
         "category": {"type": "string"},
         "limit": {"type": "integer", "description": "Max rows (default 10, max 50)."}}, ["stack_name"]),
    _fn("list_actions_required", "Top high-priority 'Actions Required' items for a stack, most affected first.",
        {"stack_name": _STACK, "limit": {"type": "integer"}}, ["stack_name"]),
    _fn("get_failed_entities", "Sample of specific entities (names, types, uids) that failed one check. Paginated via offset.",
        {"stack_name": _STACK, "check_name": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}},
        ["stack_name", "check_name"]),
    _fn("search_docs", "Semantic search over Contentstack documentation and check explanations. Use for conceptual questions: "
        "why something matters, how to fix it, what a feature is, best practices. NOT for counts, statuses or lists from the report.",
        {"query": {"type": "string", "description": "Self-contained search query, rephrased with the key concept names."},
         "category": {"type": "string", "enum": ["Security", "Content Modeling", "Content", "Other Configurations"],
                      "description": "Optional filter."}}, ["query"]),
]

def _search_docs(_db: Session, query: str, category: str | None = None) -> dict:
    return {"passages": store.search(query, k=4, category=category)}


_DISPATCH = {
    "list_stacks": queries.list_stacks, "list_checks": queries.list_checks,
    "get_stack_summary": queries.get_stack_summary, "get_check_status": queries.get_check_status,
    "list_checks_by_status": queries.list_checks_by_status,
    "list_actions_required": queries.list_actions_required, "get_failed_entities": queries.get_failed_entities,
    "search_docs": _search_docs,
}


def call_tool(db: Session, name: str, arguments_json: str) -> str:
    """Run a tool and return a JSON string.

    Tool arguments come from the LLM, so treat them as untrusted input. Every failure is returned as
    data so the model can recover; unexpected exceptions are logged with a traceback.
    """
    fn = _DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool '{name}'."})
    start = time.perf_counter()
    try:
        result = json.dumps(fn(db, **json.loads(arguments_json or "{}")))
        log.info("tool=%s ok ms=%.0f args=%s", name, (time.perf_counter() - start) * 1000, arguments_json)
        return result
    except EntityNotFound as e:
        log.info("tool=%s not_found args=%s", name, arguments_json)
        return json.dumps({"error": str(e)})
    except (json.JSONDecodeError, TypeError) as e:
        log.warning("tool=%s bad_arguments args=%s err=%s", name, arguments_json, e)
        return json.dumps({"error": f"Bad arguments: {e}"})
    except Exception:
        db.rollback()  # a failed statement leaves the session unusable until rolled back
        log.exception("tool=%s failed args=%s", name, arguments_json)
        return json.dumps({"error": "Internal error while running this tool."})
