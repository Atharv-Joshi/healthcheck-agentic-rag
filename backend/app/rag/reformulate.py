"""Query reformulation for doc retrieval. Deliberately independent of the agent loop.

The LLM call is injected as a `Completer` (system, user) -> text, so this module stays provider-agnostic and
testable without a network. Every function is fail-safe: on any error or empty output it returns the input query,
because a slightly worse query is better than no answer.
"""
import logging
import re
from collections.abc import Callable

log = logging.getLogger(__name__)

Completer = Callable[[str, str], str]
MAX_QUERY_CHARS = 200

REWRITE_SYSTEM = (
    "You rewrite a user's question into a short, self-contained search query for a documentation search engine "
    "about Contentstack (a headless CMS). Resolve vague references such as 'this one' or 'it' using the report "
    "lookups provided as context, and use the concrete feature or check name. Focus on the concept the user wants "
    "explained (importance, impact, how to fix), not on report numbers. Maximum 20 words. "
    "Output only the query: no quotes, no explanation."
)

BROADEN_SYSTEM = (
    "A documentation search returned weak results. Write ONE different search query for the same information "
    "need: use synonyms or the official Contentstack feature name, and phrase it a little more generally. "
    "Maximum 20 words. Output only the query: no quotes, no explanation."
)


def _clean(text: str, fallback: str) -> str:
    """First non-empty line, stripped of quotes and 'Query:' prefixes, length-capped."""
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(search\s+)?query\s*:\s*", "", line.strip(), flags=re.I).strip(" \t\"'`")
        line = re.sub(r"\s+", " ", line)
        if line:
            return line[:MAX_QUERY_CHARS]
    return fallback


def _prompt(user_question: str, query: str, context: list[str], label: str) -> str:
    ctx = "\n".join(f"- {c}" for c in context) or "- (none)"
    return f"User question: {user_question}\n{label}: {query}\nReport lookups so far:\n{ctx}"


def reformulate_query(complete: Completer, user_question: str, draft_query: str,
                      context: list[str] | None = None) -> str:
    """Turn a vague/conversational question (or the agent's draft query) into a clean retrieval query."""
    try:
        out = _clean(complete(REWRITE_SYSTEM, _prompt(user_question, draft_query, context or [], "Draft query")),
                     draft_query)
    except Exception:
        log.exception("query reformulation failed; using draft query")
        return draft_query
    if out != draft_query:
        log.info("reformulated query %r -> %r", draft_query, out)
    return out


def broaden_query(complete: Completer, user_question: str, failed_query: str,
                  context: list[str] | None = None) -> str:
    """A different phrasing for a retry after a weak search. Falls back to the failed query on error."""
    try:
        return _clean(complete(BROADEN_SYSTEM, _prompt(user_question, failed_query, context or [], "Weak query")),
                      failed_query)
    except Exception:
        log.exception("query broadening failed")
        return failed_query


def openai_completer(client, model: str, max_tokens: int = 80) -> Completer:
    """Adapt an OpenAI-compatible client into a Completer (deterministic, short outputs)."""
    def complete(system: str, user: str) -> str:
        resp = client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return resp.choices[0].message.content or ""
    return complete
