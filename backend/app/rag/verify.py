"""Stretch: citation check. Does the retrieved documentation actually support the answer's claims?

One cheap LLM call after the final answer, only when the answer relied on doc snippets (report facts come from
SQL and are exact, so they don't need this). Unsupported answers are FLAGGED, not silently rewritten: the client
decides how to show them. Fail-open: if the check itself errors, the answer is returned unflagged.
"""
import logging

from app.rag.reformulate import Completer

log = logging.getLogger(__name__)

VERIFY_SYSTEM = (
    "You are a strict fact-checking assistant. Given source snippets and an answer, decide whether every "
    "documentation-based claim in the answer is supported by the snippets. Statements about specific report data "
    "(counts, statuses, stack names) are out of scope; ignore them. Reply with 'yes' or 'no' on the first line, "
    "then one short sentence of reasoning."
)
MAX_SNIPPET_CHARS = 4000


def verify_answer(complete: Completer, answer: str, snippets: list[str]) -> dict:
    """-> {"status": "supported" | "unsupported" | "skipped", "reason": str}"""
    if not snippets:
        return {"status": "skipped", "reason": "answer did not rely on documentation"}
    sources = "\n---\n".join(snippets)[:MAX_SNIPPET_CHARS]
    try:
        verdict = complete(VERIFY_SYSTEM, f"Source snippets:\n{sources}\n\nAnswer:\n{answer}")
    except Exception:
        log.exception("answer verification failed; leaving answer unflagged")
        return {"status": "skipped", "reason": "verification unavailable"}
    first, _, rest = verdict.strip().partition("\n")
    supported = first.strip().lower().startswith("yes")
    if not supported:
        log.warning("UNVERIFIED answer flagged: %s", (rest or first)[:200])
    return {"status": "supported" if supported else "unsupported", "reason": (rest or first).strip()[:300]}
