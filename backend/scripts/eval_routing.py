"""Routing eval: does the agent pick the right retrieval path? Usage: python -m scripts.eval_routing
Each case lists tools that MUST be called and tools that must NOT be called."""
import sys

from app.agent import ask
from app.db.database import SessionLocal

SQL = {"list_stacks", "list_checks", "get_stack_summary", "get_check_status",
       "list_checks_by_status", "list_actions_required", "get_failed_entities"}
DOCS = {"search_docs"}

# (question, must_call: any-of groups, must_not_call)
CASES = [
    # factual -> SQL only
    ("What are the top 3 actions required for Globex Corporate Site?", [{"list_actions_required", "list_checks_by_status"}], DOCS),
    ("How many checks failed for Initech Support Portal?", [{"get_stack_summary", "list_checks_by_status"}], DOCS),
    ("What is the status of the SSO check for Acme Retail - Web?", [{"get_check_status"}], DOCS),
    ("List the failed Security checks for Globex Corporate Site.", [{"list_checks_by_status"}], DOCS),
    ("Show me a few entities that failed Unused Assets on Globex Corporate Site.", [{"get_failed_entities"}], DOCS),
    ("Which stacks were audited?", [{"list_stacks"}], DOCS),
    ("Which stack has the most failed checks?", [{"list_stacks", "get_stack_summary"}], DOCS),
    ("List all Content Modeling checks.", [{"list_checks", "list_checks_by_status"}], DOCS),
    ("How many entries does Initech Support Portal have?", [{"get_stack_summary", "list_stacks"}], DOCS),
    ("How many assets are affected by Oversized Assets in Acme Retail - Mobile App?", [{"get_check_status"}], DOCS),
    # conceptual -> docs only
    ("Why does two-factor authentication matter?", [DOCS], SQL),
    ("How do I reduce image file size for delivery?", [DOCS], SQL),
    ("What is a fallback language in Contentstack?", [DOCS], SQL),
    ("What are best practices for content modeling?", [DOCS], SQL),
    ("What is the difference between a management token and a delivery token?", [DOCS], SQL),
    ("Why are workflows useful?", [DOCS], SQL),
    # both
    ("Is SSO enabled for Acme Retail - Web, and why does it matter?", [{"get_check_status"}, DOCS], set()),
    ("What's our top action required on Globex Corporate Site and how do I fix it?", [SQL, DOCS], set()),
    ("Did Acme Retail - Web fail the Oversized Assets check? If so, how do I fix it?", [{"get_check_status"}, DOCS], set()),
    # neither / clarification
    ("What is the capital of France?", [], SQL | DOCS),
    ("Hi!", [], SQL | DOCS),
    ("How many checks failed?", [{"list_stacks"}], DOCS),  # ambiguous stack -> should look up / ask
]


# Supervision cases: (question, should_a_retry_fire). These measure the agentic part, not the routing.
# TODO(human): add 4-6 cases from what real users would actually type. Mix vague/conversational questions that
# should be rewritten and retried (e.g. ones with no concrete feature name, or typos) with clear questions that
# should NOT retry (retry=False), so the eval also catches over-eager retrying, which wastes LLM calls.
# Format: ("why should I care about this one?", True)
RETRY_CASES: list[tuple[str, bool]] = []


def main() -> None:
    passed = 0
    with SessionLocal() as db:
        for q, must, must_not in CASES:
            r = ask(db, q)
            used = {t["name"] for t in r["tool_calls"]}
            ok = all(used & group for group in must) and not (used & must_not)
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  {q}\n      tools={sorted(used)}")
            if r.get("retries"):
                print(f"      retries={[(e['kind'], e['reason']) for e in r['retries']]}")
            if not ok:
                print(f"      answer: {r['answer'][:160]!r}")

        retry_passed = 0
        for q, expect_retry in RETRY_CASES:
            r = ask(db, q)
            ok = bool(r.get("retries")) == expect_retry
            retry_passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  [retry={'yes' if expect_retry else 'no'}] {q}\n"
                  f"      retries={[(e['kind'], e['reason']) for e in r.get('retries', [])]}")

    print(f"\n{passed}/{len(CASES)} routed correctly")
    if RETRY_CASES:
        print(f"{retry_passed}/{len(RETRY_CASES)} supervision cases behaved as expected")
    sys.exit(0 if passed == len(CASES) and retry_passed == len(RETRY_CASES) else 1)


if __name__ == "__main__":
    main()
