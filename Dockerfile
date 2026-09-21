# --- build the React app ---
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- API + static frontend ---
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 CHROMA_DIR=/app/chroma_db FRONTEND_DIST=/app/frontend_dist
COPY backend/requirements.txt .
# Embeddings run on ONNX Runtime (a chromadb dependency), so there is no torch in this image
RUN pip install --no-cache-dir -r requirements.txt

# Run as an unprivileged user; a named volume mounted at CHROMA_DIR inherits this ownership
RUN useradd --create-home --uid 1000 app && mkdir -p "$CHROMA_DIR" && chown -R app:app /app
USER app
COPY --chown=app:app backend/ ./
COPY --chown=app:app --from=web /web/dist ./frontend_dist
COPY --chown=app:app docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
# Bake the ONNX embedding model into the image (cached under the app user's ~/.cache/chroma) so cold starts don't download it
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()(['warm up'])"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 CMD ["python", "-m", "scripts.healthcheck"]
ENTRYPOINT ["/docker-entrypoint.sh"]
