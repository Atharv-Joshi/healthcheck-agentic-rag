import logging
import os
from pathlib import Path

import openai
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.agent import ask
from app.db.database import SessionLocal

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="Healthcheck Q&A")
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
def ask_endpoint(request: Request, req: AskRequest, db: Session = Depends(get_db)):
    try:
        return ask(db, req.question)
    except openai.APIStatusError as e:
        raise HTTPException(502, f"LLM provider error {e.status_code}: {e.message}")
    except openai.OpenAIError as e:
        raise HTTPException(502, f"LLM client error: {e}")


# In the container the built React app is served by FastAPI itself (same origin, no CORS).
_dist = Path(os.getenv("FRONTEND_DIST", "/app/frontend_dist"))
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
