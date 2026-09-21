#!/bin/sh
set -e
# Schema from migrations and mock data on first boot (idempotent). The vector index is baked into the image at build
# time; the ingest below only runs as a fallback if the index directory is empty (e.g. an empty mounted volume).
alembic upgrade head
python -m scripts.seed --if-empty
if [ -z "$(ls -A "$CHROMA_DIR" 2>/dev/null)" ]; then python -m scripts.ingest_docs; fi
# --proxy-headers so the rate limiter sees the real client IP behind Render/Railway's proxy
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
