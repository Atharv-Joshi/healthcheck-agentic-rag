"""Stack listing for the dashboard. Everything is read from the database, so the number of cards is whatever
is seeded: adding a stack (or 20) needs no code change."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Stack


def list_stack_cards(db: Session) -> list[dict]:
    stacks = db.scalars(select(Stack).order_by(Stack.name)).all()
    by_status: dict[int, dict[str, int]] = {}
    for stack_id, status, n in db.execute(
            select(CheckResult.stack_id, CheckResult.status, func.count()).group_by(CheckResult.stack_id, CheckResult.status)):
        by_status.setdefault(stack_id, {})[status] = n
    by_bucket: dict[int, dict[str, int]] = {}
    for stack_id, bucket, n in db.execute(
            select(CheckResult.stack_id, CheckResult.bucket, func.count()).group_by(CheckResult.stack_id, CheckResult.bucket)):
        by_bucket.setdefault(stack_id, {})[bucket] = n

    cards = []
    for s in stacks:
        st, bk = by_status.get(s.id, {}), by_bucket.get(s.id, {})
        cards.append({
            "id": s.id, "name": s.name, "entries_count": s.entries_count, "assets_count": s.assets_count,
            "run_date": str(s.run_date),
            "checks": {"total": sum(st.values()), "passed": st.get("passed", 0),
                       "failed": st.get("failed", 0), "skipped": st.get("skipped", 0)},
            "actions_required": bk.get("Actions Required", 0),
            "areas_of_opportunity": bk.get("Areas of Opportunity", 0),
        })
    return cards


def get_stack(db: Session, stack_id: int) -> Stack | None:
    return db.get(Stack, stack_id)
