import os
from pathlib import Path

import openai
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent import ask as ask_raw
from app.agent_lc import ask as ask_langchain
from app.db.database import SessionLocal

app = FastAPI(title="Healthcheck Q&A")

# AGENT_IMPL=raw (hand-written loop, default) | langchain
ask = ask_langchain if os.getenv("AGENT_IMPL") == "langchain" else ask_raw


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
def ask_endpoint(req: AskRequest, db: Session = Depends(get_db)):
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
