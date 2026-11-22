"""FastAPI backend for Niki AI Assistance for Food Technology.

Run:  uvicorn main:api --host 0.0.0.0 --port 8000
The Groq key is sent by the frontend in the X-Groq-Key header on every request
and is never written to disk or logged.
"""
from typing import List, Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

import core
import doc_utils as D

api = FastAPI(title="Niki AI Assistance for Food Technology API", version="2.0")

STORES = {}          # session_id -> {"docs": {name: text}, "retriever": Retriever}
MAX_SESSIONS = 100   # simple memory cap


class Msg(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    query: str
    history: List[Msg] = []
    headers: List[dict] = []          # poster header fields chosen on the Poster page
    last_style: Optional[str] = None  # style of the previous reply (so it switches every time)
    depth: int = 0                    # follow-up level of this question (0 = typed by the user)


class PosterRequest(BaseModel):
    title: str


def use_key(key: Optional[str]):
    if not key or not key.strip():
        raise HTTPException(401, "Missing Groq API key. Paste it in the sidebar.")
    core.set_key(key.strip())


def llm_error(e: Exception):
    msg = str(e)
    low = msg.lower()
    if "401" in msg or "invalid api key" in low or "invalid_api_key" in low:
        return HTTPException(401, "Groq rejected the API key. Check it and try again.")
    if "429" in msg or "rate limit" in low:
        return HTTPException(429, "Groq rate limit reached. Wait a moment and retry.")
    return HTTPException(502, f"Model error: {msg[:300]}")


@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/extract")
async def extract(session_id: str = Form(...), files: List[UploadFile] = File(...)):
    docs, warnings = {}, []
    for f in files:
        data = await f.read()
        try:
            text = D.extract_text(f.filename or "file", data)
        except Exception as e:
            warnings.append(f"{f.filename}: could not read ({e})")
            continue
        if text.strip():
            docs[f.filename] = text
        else:
            warnings.append(f"{f.filename}: no text found (install Tesseract for scanned files).")
    if len(STORES) >= MAX_SESSIONS and session_id not in STORES:
        STORES.pop(next(iter(STORES)))
    STORES[session_id] = {"docs": docs, "retriever": D.Retriever(docs) if docs else None}
    return {"loaded": list(docs), "warnings": warnings}


@api.delete("/session/{session_id}")
def clear_session(session_id: str):
    STORES.pop(session_id, None)
    return {"cleared": True}


@api.post("/chat")
def chat(req: ChatRequest, x_groq_key: Optional[str] = Header(default=None)):
    """Answers a question, or - when the message asks for it - creates a poster, image,
    pptx, pdf, docx, xlsx or txt. Always returns answer, followups, blocked, style, files[]."""
    use_key(x_groq_key)
    query = req.query.strip()
    if not query:
        raise HTTPException(422, "Empty question.")
    history = [m.model_dump() for m in req.history]
    store = STORES.get(req.session_id)
    retriever = store["retriever"] if store else None
    try:
        intent = core.detect_create(query)
        if intent:
            ctx = retriever.context(intent["topic"] or query) if retriever else ""
            res = core.create(intent, query, history, ctx, req.headers, req.last_style)
            if req.depth >= core.MAX_FOLLOWUP_LEVELS:
                res["followups"] = []
        else:
            ctx = retriever.context(query) if retriever else ""
            res = core.respond(query, history, ctx, req.last_style, depth=req.depth)
        res.setdefault("files", [])
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise llm_error(e)


@api.post("/poster")
def poster(req: PosterRequest, x_groq_key: Optional[str] = Header(default=None)):
    use_key(x_groq_key)
    if not req.title.strip():
        raise HTTPException(422, "Empty title.")
    try:
        content = core.poster_content(req.title.strip())
    except Exception as e:
        raise llm_error(e)
    if not content:
        raise HTTPException(422, "I can only create posters on food technology topics.")
    return {"content": content}
