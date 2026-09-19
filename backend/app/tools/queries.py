"""SQL-backed tools the agent can call. Each returns a JSON-serializable dict."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Check, CheckResult, FailedEntity, Stack

MAX_LIMIT = 50


class LookupError_(Exception):
    """Raised when a stack/check name is unknown or ambiguous; message is shown to the LLM."""


def _resolve_stack(db: Session, name: str) -> Stack:
    matches = db.scalars(select(Stack).where(Stack.name.ilike(f"%{name}%"))).all()
    if len(matches) == 1:
        return matches[0]
    if not matches:
        known = [s.name for s in db.scalars(select(Stack))]
        raise LookupError_(f"No stack matches '{name}'. Known stacks: {known}")
    raise LookupError_(f"'{name}' is ambiguous. Candidates: {[s.name for s in matches]}")


def _resolve_check(db: Session, name: str) -> Check:
    matches = db.scalars(select(Check).where(Check.name.ilike(f"%{name}%"))).all()
    exact = [c for c in matches if c.name.lower() == name.lower()]
    if len(exact) == 1:
        return exact[0]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise LookupError_(f"No check matches '{name}'. Use list_checks to see check names.")
    raise LookupError_(f"'{name}' is ambiguous. Candidates: {[c.name for c in matches]}")


def list_stacks(db: Session) -> dict:
    return {"stacks": [
        {"name": s.name, "entries": s.entries_count, "assets": s.assets_count, "run_date": str(s.run_date)}
        for s in db.scalars(select(Stack).order_by(Stack.name))
    ]}


def list_checks(db: Session, category: str | None = None) -> dict:
    q = select(Check).order_by(Check.category, Check.name)
    if category:
        q = q.where(Check.category.ilike(f"%{category}%"))
    return {"checks": [{"name": c.name, "category": c.category} for c in db.scalars(q)]}


def get_stack_summary(db: Session, stack_name: str) -> dict:
    stack = _resolve_stack(db, stack_name)
    by_status = dict(db.execute(
        select(CheckResult.status, func.count()).where(CheckResult.stack_id == stack.id).group_by(CheckResult.status)
    ).all())
    by_bucket = dict(db.execute(
        select(CheckResult.bucket, func.count()).where(CheckResult.stack_id == stack.id).group_by(CheckResult.bucket)
    ).all())
    return {"stack": stack.name, "entries": stack.entries_count, "assets": stack.assets_count,
            "run_date": str(stack.run_date), "checks_by_status": by_status, "checks_by_bucket": by_bucket}


def get_check_status(db: Session, stack_name: str, check_name: str) -> dict:
    stack, check = _resolve_stack(db, stack_name), _resolve_check(db, check_name)
    r = db.scalar(select(CheckResult).where(CheckResult.stack_id == stack.id, CheckResult.check_id == check.id))
    return {"stack": stack.name, "check": check.name, "category": check.category, "status": r.status,
            "bucket": r.bucket, "affected_entities": r.entity_count,
            "description": check.description, "recommendation": check.recommendation_text}


def list_checks_by_status(db: Session, stack_name: str, status: str | None = None,
                          bucket: str | None = None, category: str | None = None, limit: int = 10) -> dict:
    """Filter a stack's results by status (passed/failed/skipped), bucket and/or category, worst first."""
    stack = _resolve_stack(db, stack_name)
    q = (select(Check.name, Check.category, CheckResult.status, CheckResult.bucket, CheckResult.entity_count)
         .join(Check, Check.id == CheckResult.check_id)
         .where(CheckResult.stack_id == stack.id)
         .order_by(CheckResult.entity_count.desc(), Check.name))
    if status:
        q = q.where(CheckResult.status == status.lower())
    if bucket:
        q = q.where(CheckResult.bucket.ilike(f"%{bucket}%"))
    if category:
        q = q.where(Check.category.ilike(f"%{category}%"))
    rows = db.execute(q).all()
    return {"stack": stack.name, "total_matching": len(rows), "returned": min(len(rows), min(limit, MAX_LIMIT)),
            "results": [{"check": n, "category": c, "status": s, "bucket": b, "affected_entities": e}
                        for n, c, s, b, e in rows[:min(limit, MAX_LIMIT)]]}


def list_actions_required(db: Session, stack_name: str, limit: int = 10) -> dict:
    return list_checks_by_status(db, stack_name, bucket="Actions Required", limit=limit)


def get_failed_entities(db: Session, stack_name: str, check_name: str, limit: int = 10, offset: int = 0) -> dict:
    """Paginated sample of entities that failed a check. affected_entities is the true total."""
    stack, check = _resolve_stack(db, stack_name), _resolve_check(db, check_name)
    r = db.scalar(select(CheckResult).where(CheckResult.stack_id == stack.id, CheckResult.check_id == check.id))
    limit = min(limit, MAX_LIMIT)
    rows = db.scalars(select(FailedEntity).where(FailedEntity.check_result_id == r.id)
                      .order_by(FailedEntity.id).limit(limit).offset(offset)).all()
    return {"stack": stack.name, "check": check.name, "status": r.status, "affected_entities": r.entity_count,
            "note": "Only a sample of affected entities is stored.",
            "entities": [{"name": e.entity_name, "type": e.entity_type, **e.extra} for e in rows]}
