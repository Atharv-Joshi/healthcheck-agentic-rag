#!/bin/sh
set -e
# Schema from migrations, mock data and vector index on first boot only (both steps are idempotent).
alembic upgrade head
python -m scripts.seed --if-empty
if [ -z "$(ls -A "$CHROMA_DIR" 2>/dev/null)" ]; then python -m scripts.ingest_docs; fi
# --proxy-headers so the rate limiter sees the real client IP behind Render/Railway's proxy
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
