#!/bin/sh
set -e
# Seed mock data and build the vector index on first boot only.
python - <<'PY'
from sqlalchemy import inspect, select, func
from app.db.database import engine, SessionLocal
from app.db.models import Stack
if not inspect(engine).has_table("stacks"):
    need = True
else:
    with SessionLocal() as db:
        need = db.scalar(select(func.count()).select_from(Stack)) == 0
open("/tmp/need_seed", "w").write("1" if need else "0")
PY
if [ "$(cat /tmp/need_seed)" = "1" ]; then python -m scripts.seed; fi
if [ -z "$(ls -A "$CHROMA_DIR" 2>/dev/null)" ]; then python -m scripts.ingest_docs; fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
