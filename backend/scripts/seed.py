"""Load reproducible mock Healthcheck data into Postgres. The schema comes from Alembic (alembic upgrade head).
Usage: python -m scripts.seed [--force | --if-empty]
  --force     replace existing data (required if the DB already has stacks)
  --if-empty  seed only when empty, otherwise do nothing (used by the container entrypoint)"""
import random
import sys
from datetime import date, timedelta

from sqlalchemy import func, select, text

from app.db import models
from app.db.database import SessionLocal, engine

from .catalog import CHECKS, ENTITY_WORDS, STACKS

MAX_SAMPLE_ENTITIES = 25  # entity_count is the true total; failed_entities holds a sample


def main(force: bool = False, if_empty: bool = False) -> None:
    rng = random.Random(42)
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(models.Stack))
    if existing and if_empty:
        print(f"Database already seeded ({existing} stacks); skipping.")
        return
    if existing and not force:
        raise SystemExit(f"Refusing to seed: database already has {existing} stacks. "
                         f"Re-run with --force to wipe and replace the mock data.")
    with engine.begin() as conn:  # data only; never touches the schema
        conn.execute(text("TRUNCATE failed_entities, check_results, checks, stacks RESTART IDENTITY CASCADE"))

    with SessionLocal() as db:
        checks = []
        for category, name, desc, rec, *_ in CHECKS:
            c = models.Check(category=category, name=name, description=desc, recommendation_text=rec)
            db.add(c)
            checks.append(c)
        stacks = []
        for i, (name, entries, assets) in enumerate(STACKS):
            s = models.Stack(name=name, entries_count=entries, assets_count=assets,
                             run_date=date(2026, 9, 1) + timedelta(days=i * 3))
            db.add(s)
            stacks.append(s)
        db.flush()

        for stack in stacks:
            for check, (_, _, _, _, etype, severity, fail_p) in zip(checks, CHECKS):
                roll = rng.random()
                if roll < 0.05:
                    status, bucket, count = "skipped", "Not Applicable", 0
                elif roll < 0.05 + fail_p * 0.95:
                    status = "failed"
                    bucket = "Actions Required" if severity == "high" else "Areas of Opportunity"
                    cap = stack.assets_count if etype == "asset" else stack.entries_count
                    count = 1 if etype in ("stack", "organization") else rng.randint(1, max(2, min(cap // 4, 900)))
                else:
                    status, bucket, count = "passed", "Strengths", 0
                res = models.CheckResult(stack_id=stack.id, check_id=check.id, status=status,
                                         bucket=bucket, entity_count=count)
                db.add(res)
                db.flush()
                for _ in range(min(count, MAX_SAMPLE_ENTITIES)):
                    word = rng.choice(ENTITY_WORDS)
                    db.add(models.FailedEntity(
                        check_result_id=res.id,
                        entity_name=f"{word}-{rng.randint(1, 999)}",
                        entity_type=etype,
                        extra={"uid": f"blt{rng.getrandbits(48):012x}",
                               "last_modified_days_ago": rng.randint(1, 900)},
                    ))
        db.commit()

        print(f"Seeded {len(checks)} checks, {len(stacks)} stacks")


if __name__ == "__main__":
    main(force="--force" in sys.argv, if_empty="--if-empty" in sys.argv)
