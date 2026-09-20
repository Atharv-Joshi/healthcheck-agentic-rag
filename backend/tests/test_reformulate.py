from app.rag.reformulate import MAX_QUERY_CHARS, broaden_query, openai_completer, reformulate_query


def stub(reply):
    calls = []

    def complete(system, user):
        calls.append((system, user))
        return reply
    complete.calls = calls
    return complete


def test_reformulation_uses_question_draft_and_report_context():
    c = stub("importance and business impact of SSO Enabled check failing")
    out = reformulate_query(c, "why should I care about this one?", "this one", ["get_check_status -> SSO Enabled failed"])
    assert out == "importance and business impact of SSO Enabled check failing"
    _, user = c.calls[0]
    assert "why should I care about this one?" in user and "SSO Enabled failed" in user


def test_output_is_sanitized():
    assert reformulate_query(stub('  Query: "why SSO matters"  \nextra explanation'), "q", "d") == "why SSO matters"


def test_output_is_length_capped():
    assert len(reformulate_query(stub("word " * 200), "q", "d")) <= MAX_QUERY_CHARS


def test_empty_output_falls_back_to_draft():
    assert reformulate_query(stub("  \n "), "q", "the draft") == "the draft"


def test_llm_failure_falls_back_to_draft():
    def boom(system, user):
        raise TimeoutError()
    assert reformulate_query(boom, "q", "the draft") == "the draft"
    assert broaden_query(boom, "q", "failed query") == "failed query"


def test_broaden_asks_for_a_different_query():
    c = stub("multi-factor authentication")
    assert broaden_query(c, "why 2fa", "2fa") == "multi-factor authentication"
    assert "weak" in c.calls[0][0].lower()


def test_openai_completer_adapts_the_client():
    from types import SimpleNamespace as NS
    seen = {}

    def create(**kw):
        seen.update(kw)
        return NS(choices=[NS(message=NS(content="rewritten"))])

    complete = openai_completer(NS(chat=NS(completions=NS(create=create))), "m")
    assert complete("sys", "usr") == "rewritten" and seen["temperature"] == 0
    assert seen["messages"][0] == {"role": "system", "content": "sys"}
