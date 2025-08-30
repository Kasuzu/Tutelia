# app.py
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Vector & LLM (compartidos)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI

# Routers modulares
from advisor import create_advisor_router           # /advisor (prefijo interno en el router)
from tutela import create_router as create_tutela_router  # /wizard (prefijo aquí)

# =======================
# ENV & CONFIG
# =======================
load_dotenv()

BASE_DIR         = Path(__file__).resolve().parent
# Tus HTML (index.html, asesor.html, tutela.html, render.html) viven en la raíz del proyecto:
UI_DIR           = BASE_DIR                         # <— importante: aquí están tus html
STATIC_DIR       = BASE_DIR / "static"              # si tienes assets (css/js/img) en ./static
DOCS_DIR         = BASE_DIR / "docs"

PERSIST_DIR      = os.getenv("PERSIST_DIR", "./chroma")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
TOP_K_DEFAULT    = int(os.getenv("TOP_K", "6"))

OPENAI_API_BASE  = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "lm-studio")
LLM_MODEL        = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE", "0.2"))
MAX_TOKENS_STEP  = int(os.getenv("MAX_TOKENS_STEP", "1024"))

EXPORT_DIR       = os.getenv("EXPORT_DIR", "./exports")
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(PERSIST_DIR, exist_ok=True)  # asegura la carpeta de Chroma

# =======================
# FASTAPI APP
# =======================
app = FastAPI(
    title="Asistente Jurídico (Tutela COL) – Modular",
    version="1.3.0",
    description="Backend FastAPI que une el asesor jurídico (RAG+memoria) y el generador de tutelas (wizard).",
)

# CORS (endurece en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # cambia a tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],            # permite GET/POST/PUT/PATCH/DELETE/OPTIONS
    allow_headers=["*"],
)

# Estáticos
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(DOCS_DIR)), name="docs")
# Montamos /exports para descargas (docx/json)
app.mount("/exports", StaticFiles(directory=str(EXPORT_DIR)), name="exports")
# Montamos /ui apuntando a la raíz del proyecto (donde están index.html, asesor.html, tutela.html, render.html)
app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")

# Root → landing (redirige al index que está en /ui/)
@app.get("/")
def root():
    return RedirectResponse("/static/index.html", status_code=302)

# Atajos cómodos para las páginas clave
@app.get("/asesor")
def go_asesor():
    return RedirectResponse("/ui/asesor.html", status_code=302)

@app.get("/tutela")
def go_tutela():
    return RedirectResponse("/ui/tutela.html", status_code=302)

@app.get("/render")
def go_render():
    # nueva pantalla final editable
    return RedirectResponse("/ui/render.html", status_code=302)

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

# =======================
# RAG COMPARTIDO (1 sola vez)
# =======================
# Embeddings deben coincidir con ingest.py
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# Vector store persistente
vectordb = Chroma(embedding_function=embeddings, persist_directory=PERSIST_DIR)

# Retriever con MMR para mayor diversidad de pasajes
retriever = vectordb.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": TOP_K_DEFAULT,
        "fetch_k": max(12, TOP_K_DEFAULT * 3),
        "lambda_mult": 0.7
    },
)

# LLM (LM Studio / OpenAI-compatible)
llm = ChatOpenAI(
    model=LLM_MODEL,
    openai_api_base=OPENAI_API_BASE,
    openai_api_key=OPENAI_API_KEY,
    temperature=LLM_TEMPERATURE,
    max_tokens=MAX_TOKENS_STEP,
)

# =======================
# INTEGRAR MÓDULOS
# =======================
# advisor: recibe vectordb para calcular scores en citas.
advisor_router = create_advisor_router(
    retriever=retriever,
    llm=llm,
    vectordb=vectordb,
    top_k_default=TOP_K_DEFAULT,
    max_tokens_default=MAX_TOKENS_STEP,
)

tutela_router = create_tutela_router(
    retriever=retriever,
    llm=llm,
    export_dir=EXPORT_DIR,
    top_k_default=TOP_K_DEFAULT,
    max_tokens_default=MAX_TOKENS_STEP,
)

# Montamos los routers
# OJO: advisor_router ya incluye su prefijo "/advisor" internamente.
app.include_router(advisor_router)

# El de tutela lo exponemos bajo "/wizard"
app.include_router(tutela_router, prefix="/wizard", tags=["tutela"])

# =======================
# MAIN (dev)
# =======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
