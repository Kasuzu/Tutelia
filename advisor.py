# advisor.py
# Asesor de tutelas (Colombia) con RAG y citas estructuradas + enlaces a la fuente.

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path
from urllib.parse import quote as urlquote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# =========================
# Config por ENV
# =========================
DISCLAIMER = "Esto es apoyo informativo; no sustituye asesoría legal profesional."
STRICT_CONTEXT = os.getenv("STRICT_CONTEXT", "0").strip().lower() in ("1", "true", "yes")

# Enlaces a fuentes (PDF.js opcional)
PDFJS_ENABLE = os.getenv("PDFJS_ENABLE", "0").strip().lower() in ("1", "true", "yes")
PDFJS_VIEWER = os.getenv("PDFJS_VIEWER", "/static/pdfjs/web/viewer.html")  # si copias PDF.js en /static/pdfjs

# =========================
# Modelos Pydantic
# =========================
class StartReq(BaseModel):
    system_hint: Optional[str] = None

class StartResp(BaseModel):
    session_id: str
    message: str

class ChatReq(BaseModel):
    session_id: str
    message: str
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None

class Citation(BaseModel):
    source: str
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    score: Optional[float] = None
    snippet: str
    url: Optional[str] = None

class ChatResp(BaseModel):
    answer: str
    session_id: str
    sources: List[Citation]

# =========================
# Estado simple en memoria
# =========================
SESSIONS: Dict[str, Dict[str, Any]] = {}

# =========================
# Helpers
# =========================
def _format_history(messages: List[Dict[str, str]], max_chars: int = 4000) -> str:
    out: List[str] = []
    for m in messages[-12:]:
        r = m.get("role", "")
        if r == "system":
            continue
        tag = "Usuario" if r == "user" else "Asesor"
        c = (m.get("content") or "").strip()
        if c:
            out.append(f"{tag}: {c}")
    return "\n".join(out)[-max_chars:]

def _format_docs(docs: List[Any], max_chars: int = 8000) -> str:
    buff: List[str] = []
    for d in docs:
        meta = getattr(d, "metadata", {}) or {}
        src = meta.get("source", "desconocido")
        page = meta.get("page")
        header = f"[source: {src}" + (f" | p.{page}]" if page is not None else "]")
        content = (getattr(d, "page_content", "") or "").strip()
        buff.append(header + "\n" + content)
    return ("\n\n---\n\n".join(buff))[:max_chars]

def _llm_invoke(llm: Any, prompt: str) -> str:
    # ChatModel .invoke → BaseMessage
    if hasattr(llm, "invoke"):
        out = llm.invoke(prompt)
        content = getattr(out, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(out, str):
            return out.strip()
        return str(out).strip()
    # LLM .predict
    if hasattr(llm, "predict"):
        return (llm.predict(prompt) or "").strip()
    # Callable
    if callable(llm):
        return (llm(prompt) or "").strip()
    raise RuntimeError("LLM no compatible (invoke/predict/callable).")

def _crop(txt: str, n: int = 240) -> str:
    if not txt:
        return ""
    s = txt[:n]
    if "\n" in s:
        s = s.rsplit("\n", 1)[0]
    return s.strip()

def _build_prompt(question: str, history: str, context: str, system_hint: Optional[str]) -> str:
    system = system_hint or (
        "Eres un asistente jurídico especializado en acciones de tutela en Colombia. "
        "Responde de forma clara, breve y accionable. Incluye, cuando proceda, inmediatez, "
        "subsidiariedad y legitimación por activa/pasiva. No inventes jurisprudencia ni artículos; "
        "apóyate en el contexto proporcionado."
    )
    return (
        f"{system}\n\n"
        f"=== HISTORIAL ===\n{history}\n\n"
        f"=== CONTEXTO (fragmentos recuperados) ===\n{context}\n\n"
        f"=== PREGUNTA ===\n{question}\n\n"
        f"Indica pasos concretos sólo cuando aporten valor. Si falta base documental, dilo."
    )

def _build_source_url(source: str, page: Optional[int], snippet: str) -> str:
    """
    Devuelve URL navegable:
      - PDFs: /docs/<file>#page=N  (o PDF.js: /static/pdfjs/web/viewer.html?file=/docs/...#page=N&search=...)
      - Otros: /docs/<file>
    """
    safe_src = urlquote(source)  # conserva subcarpetas
    path = f"/docs/{safe_src}"
    ext = Path(source).suffix.lower()

    if ext == ".pdf" and page is not None:
        if PDFJS_ENABLE:
            from urllib.parse import quote as q
            search = q((snippet or "")[:80])
            return f"{PDFJS_VIEWER}?file={q(path)}#page={int(page)}&search={search}"
        return f"{path}#page={int(page)}"
    return path

# =========================
# Core (fábrica de routers)
# =========================
def _build_router(
    *,
    retriever: Any,
    llm: Any,
    vectordb: Any = None,
    prefix: str = "",         # "" para usar prefix en app.include_router; "/advisor" para auto-prefijo
    top_k_default: int = 6,
    max_tokens_default: int = 1024,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["advisor"] if prefix else None)

    @router.post("/start", response_model=StartResp)
    def start(req: StartReq = StartReq()) -> StartResp:
        sid = str(uuid.uuid4())
        system_msg = req.system_hint or "Actúa como asesor en acciones de tutela (Colombia)."
        SESSIONS[sid] = {"messages": [{"role": "system", "content": system_msg}]}
        return StartResp(session_id=sid, message="¡Hola! Soy tu asesor en acciones de tutela (Colombia). ¿Qué te preocupa?")

    @router.post("/answer", response_model=ChatResp)
    def answer(req: ChatReq) -> ChatResp:
        sid = (req.session_id or "").strip()
        if not sid or sid not in SESSIONS:
            raise HTTPException(status_code=400, detail="session_id inválido o inexistente.")

        top_k = req.top_k if req.top_k and req.top_k > 0 else top_k_default
        _ = req.max_tokens or max_tokens_default  # reservado para LLMs que lo soporten

        sess = SESSIONS[sid]
        messages: List[Dict[str, str]] = sess.setdefault("messages", [])

        # ===== 1) Recuperación
        try:
            if hasattr(retriever, "invoke"):
                docs = retriever.invoke(req.message)
            elif hasattr(retriever, "get_relevant_documents"):
                docs = retriever.get_relevant_documents(req.message)
            else:
                docs = []
        except Exception:
            docs = []

        # ===== 2) Sin contexto (modo estricto)
        if not docs and STRICT_CONTEXT:
            answer_text = (
                "No encontré base en el índice para responder con respaldo documental. "
                "Carga o indexa la norma o sentencia pertinente y vuelve a preguntar.\n\n"
                "Fuentes:\n- (sin fuentes en el índice)\n\n"
                f"{DISCLAIMER}"
            )
            messages.append({"role": "user", "content": req.message})
            messages.append({"role": "assistant", "content": answer_text})
            return ChatResp(answer=answer_text, session_id=sid, sources=[])

        # ===== 3) Contexto + historial
        context = _format_docs(docs)
        history_text = _format_history(messages)

        # ===== 4) Prompt y LLM
        system_hint = next((m.get("content") for m in messages if m.get("role") == "system"), None)
        prompt = _build_prompt(req.message, history_text, context, system_hint)
        raw_answer = _llm_invoke(llm, prompt).strip()

        # ===== 5) Citas (con score si hay vectordb)
        score_by_chunk: Dict[str, float] = {}
        if vectordb is not None:
            try:
                scored = vectordb.similarity_search_with_score(req.message, k=top_k)
                for d, s in scored:
                    cid = (getattr(d, "metadata", {}) or {}).get("chunk_id")
                    if cid:
                        score_by_chunk[cid] = float(s)
            except Exception:
                pass

        citations: List[Citation] = []
        for d in docs:
            meta = getattr(d, "metadata", {}) or {}
            src = meta.get("source", "desconocido")
            pg = meta.get("page")
            snip = _crop(getattr(d, "page_content", "") or "", 240)
            citations.append(
                Citation(
                    source=src,
                    page=pg,
                    chunk_id=meta.get("chunk_id"),
                    score=score_by_chunk.get(meta.get("chunk_id")),
                    snippet=snip,
                    url=_build_source_url(src, pg, snip),
                )
            )

        # ===== 6) Texto final (Fuentes + disclaimer una sola vez)
        sources_text = "\n".join(
            f"- {c.source}" + (f" (p. {c.page})" if c.page is not None else "") + (f" — `{c.chunk_id}`" if c.chunk_id else "")
            for c in citations
        ) or "- (sin fuentes en el índice)"

        final_answer = f"{raw_answer}\n\nFuentes:\n{sources_text}\n\n{DISCLAIMER}".strip()

        # Persistir conversación
        messages.append({"role": "user", "content": req.message})
        messages.append({"role": "assistant", "content": final_answer})

        return ChatResp(answer=final_answer, session_id=sid, sources=citations)

    # Alias opcional por compatibilidad con front antiguo (/chat)
    @router.post("/chat", response_model=ChatResp)
    def chat(req: ChatReq) -> ChatResp:
        return answer(req)

    return router

# =========================
# Factories públicas (compatibles con tus dos estilos de app.py)
# =========================
def create_advisor_router(
    retriever: Any,
    llm: Any,
    vectordb: Any = None,
    top_k_default: int = 6,
    max_tokens_default: int = 1024,
) -> APIRouter:
    """
    Devuelve un APIRouter **con prefijo interno '/advisor'**.
    Úsalo así en app.py:
        app.include_router(create_advisor_router(...))
    """
    return _build_router(
        retriever=retriever,
        llm=llm,
        vectordb=vectordb,
        prefix="/advisor",
        top_k_default=top_k_default,
        max_tokens_default=max_tokens_default,
    )

def create_router(
    retriever: Any,
    llm: Any,
    top_k_default: int = 6,
    max_tokens_default: int = 1024,
    vectordb: Any = None,
) -> APIRouter:
    """
    Devuelve un APIRouter **SIN prefijo** (para incluir con prefix="/advisor").
    Compatible con tu app.py anterior:
        app.include_router(create_router(...), prefix="/advisor", tags=["advisor"])
    """
    return _build_router(
        retriever=retriever,
        llm=llm,
        vectordb=vectordb,
        prefix="",  # sin prefijo interno
        top_k_default=top_k_default,
        max_tokens_default=max_tokens_default,
    )
