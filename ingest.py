# ingest.py
# Ingesta de documentos para RAG (Chroma + HF Embeddings)
# - Crea chunks con CHUNK_SIZE / CHUNK_OVERLAP
# - Normaliza metadatos: source (ruta relativa), page (si aplica)
# - Añade chunk_id estable: <ruta_sin_ext>:p<page|na>:<hash10>
# - Si CLEAR=1, borra el índice antes de re-crear

import os
import shutil
import hashlib
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Load env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs")).resolve()
PERSIST_DIR = os.getenv("PERSIST_DIR", "./chroma")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
CLEAR = os.getenv("CLEAR", "0").strip() in ("1", "true", "True", "yes", "YES")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")


# -----------------------------
# Loaders
# -----------------------------
def load_documents() -> List[Document]:
    """Carga PDFs, DOCX, TXT y MD desde DOCS_DIR."""
    from langchain_community.document_loaders import (
        DirectoryLoader,
        TextLoader,
        PyPDFLoader,
        Docx2txtLoader,
    )

    def _dl(pattern, loader_cls, **loader_kwargs):
        return DirectoryLoader(
            str(DOCS_DIR),
            glob=pattern,
            loader_cls=loader_cls,
            loader_kwargs=loader_kwargs or None,
            use_multithreading=True,
            silent_errors=True,
        )

    loaders = [
        _dl("**/*.pdf", PyPDFLoader),
        _dl("**/*.docx", Docx2txtLoader),
        _dl("**/*.txt", TextLoader, encoding="utf-8"),
        _dl("**/*.md", TextLoader, encoding="utf-8"),
    ]

    docs: List[Document] = []
    for ld in loaders:
        try:
            docs.extend(ld.load())
        except Exception as e:
            print(f"[WARN] Loader falló: {ld}: {e}")

    # Normaliza 'source' a ruta relativa al DOCS_DIR
    normed: List[Document] = []
    for d in docs:
        meta = d.metadata or {}
        src = meta.get("source") or meta.get("file_path") or ""
        try:
            if src:
                srcp = Path(src)
                if srcp.is_absolute():
                    src = srcp.resolve().relative_to(DOCS_DIR).as_posix()
                else:
                    src = Path(src).as_posix()
        except Exception:
            # si no se puede relativizar, deja tal cual
            src = str(src)
        meta["source"] = src or "desconocido"
        d.metadata = meta
        normed.append(d)

    print(f"[INGEST] Documentos cargados: {len(normed)}")
    return normed


# -----------------------------
# Chunks + metadatos
# -----------------------------
def _hash10(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:10]

def split_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    for i, d in enumerate(chunks):
        meta = d.metadata or {}
        src = meta.get("source", "desconocido").replace("\\", "/")
        page = meta.get("page", None)
        # chunk_id estable: base de ruta sin extensión + page + hash del contenido
        base = Path(src).with_suffix("").as_posix()
        h = _hash10(d.page_content or "")
        ptag = f"p{page}" if page is not None else "pna"
        meta["chunk_id"] = f"{base}:{ptag}:{h}"
        meta["chunk_index"] = i  # índice útil para depurar
        d.metadata = meta

    print(f"[INGEST] Chunks generados: {len(chunks)} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    return chunks


# -----------------------------
# Persistencia en Chroma
# -----------------------------
def build_index(chunks: List[Document]) -> None:
    if CLEAR:
        print(f"[INGEST] CLEAR=1 → borrando índice en {PERSIST_DIR} …")
        shutil.rmtree(PERSIST_DIR, ignore_errors=True)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Persistencia automática con persist_directory (no llames .persist())
    vectordb = Chroma(embedding_function=embeddings, persist_directory=PERSIST_DIR)

    # (Opcional) evita duplicados si reingestas sin CLEAR usando IDs estables
    try:
        ids = [d.metadata.get("chunk_id") for d in chunks]
        vectordb.add_documents(chunks, ids=ids)
    except Exception:
        # fallback si tu versión no soporta ids=
        vectordb.add_documents(chunks)

    # Imprime muestra de 3 chunks
    print("[INGEST] Ejemplos de metadatos:")
    for d in chunks[:3]:
        print({
            "source": d.metadata.get("source"),
            "page": d.metadata.get("page"),
            "chunk_id": d.metadata.get("chunk_id"),
            "chars": len(d.page_content or ""),
        })

    print(f"[INGEST] Index listo en {PERSIST_DIR}")



# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    if not DOCS_DIR.exists():
        raise SystemExit(f"[ERROR] No existe DOCS_DIR: {DOCS_DIR}")

    docs = load_documents()
    if not docs:
        raise SystemExit("[ERROR] No se encontraron documentos en DOCS_DIR.")

    chunks = split_documents(docs)
    build_index(chunks)
