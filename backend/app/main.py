import asyncio
import logging
from contextlib import asynccontextmanager

import openai
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.agent import ask
from app.config import get_settings
from app.db.database import SessionLocal
from app.rag import store

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Warm the embedding model in the background. uvicorn binds the port only AFTER lifespan startup completes,
    so awaiting the warm-up here would keep the port closed (a free-tier CPU took minutes, past Render's port-scan
    timeout). Requests that arrive first simply wait on the store's lock."""
    async def warm() -> None:
        try:
            await asyncio.to_thread(store.warm_up)
        except Exception:
            log.exception("vector store warm-up failed; docs search will retry lazily")

    task = asyncio.create_task(warm())  # keep a reference so it isn't garbage-collected mid-run
    yield
    task.cancel()


app = FastAPI(title="Healthcheck Q&A", lifespan=lifespan)
# Every /ask costs LLM money. Behind a reverse proxy run uvicorn with --proxy-headers so this sees the client IP.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_db():
    with SessionLocal() as db:
        yield db


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    answer: str
    tool_calls: list[dict]
    retries: list[dict] = []           # supervised retries triggered while answering
    verification: dict | None = None   # citation check result (when VERIFY_ANSWERS=true)
    off_topic: bool = False            # True when the question was declined as out of scope


@app.get("/health")
def health():
    return {"status": "ok"}


# All API routes live under /api, in dev and in production. In production the built React app is mounted at "/",
# and a static mount only accepts GET, so an unprefixed POST /ask from the browser would be caught by it (405).
api = APIRouter(prefix="/api")


@api.post("/ask", response_model=AskResponse)
@limiter.limit(settings.rate_limit)
def ask_endpoint(request: Request, req: AskRequest, db: Session = Depends(get_db)):
    try:
        return ask(db, req.question)
    except openai.APIStatusError as e:
        raise HTTPException(502, f"LLM provider error {e.status_code}: {e.message}")
    except openai.OpenAIError as e:
        raise HTTPException(502, f"LLM client error: {e}")


app.include_router(api)


def mount_frontend(target: FastAPI, dist_dir) -> None:
    """Serve the built React app from "/" (same origin as the API, so no CORS). Must be mounted LAST."""
    target.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")


if settings.frontend_dist.is_dir():
    mount_frontend(app, settings.frontend_dist)
