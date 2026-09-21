"""Conversation memory. The server is stateless: the browser sends the recent messages with every question.

The history is client-supplied, so it is treated as untrusted text: only user/assistant roles are accepted, each
message is truncated, and only the most recent turns are kept. Nothing in it can widen what the tools may access,
because the stack scope is enforced server-side (tools/supervisor.py), not by anything the history says.
"""
MAX_MESSAGES = 10   # ~5 turns: enough for follow-ups, small enough to keep every request cheap
MAX_CHARS = 1500


def clean_history(history: list[dict] | None) -> list[dict]:
    msgs = []
    for m in history or []:
        role, content = m.get("role"), m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            msgs.append({"role": role, "content": content.strip()[:MAX_CHARS]})
    msgs = msgs[-MAX_MESSAGES:]
    while msgs and msgs[0]["role"] != "user":  # a window that starts mid-answer confuses the model
        msgs.pop(0)
    return msgs


def conversation_notes(history: list[dict]) -> list[str]:
    """Short context lines for the docs-query reformulator, so 'why does that matter?' can be resolved."""
    notes = [f"Earlier user question: {m['content'][:200]}" for m in [m for m in history if m["role"] == "user"][-2:]]
    last_answer = next((m for m in reversed(history) if m["role"] == "assistant"), None)
    if last_answer:
        notes.append(f"Previous answer (excerpt): {last_answer['content'][:240]}")
    return notes
