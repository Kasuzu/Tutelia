# Asistente Jurídico (Tutela COL) — RAG + Wizard

Asistente full-stack para **redactar acciones de tutela en Colombia** con apoyo de IA y **RAG** (búsqueda semántica sobre normas/sentencias). Incluye un **wizard** que guía el diligenciamiento, **persistencia en SQLite**, **mejoras automáticas de texto**, **exportación a DOCX/JSON** y compatibilidad con **modelos LLM locales** vía **LM Studio** (p. ej., modelos **pequeños** tipo *Gemma 3* / *GEMA3*, que permiten ejecutar en PCs modestos e incluso mini‑PCs). También puedes conectarlo a un endpoint remoto (online).

<p align="left">
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10–3.12-blue.svg"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-1.x-009688.svg"></a>
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green.svg">
  <img alt="Status" src="https://img.shields.io/badge/Status-Active-success.svg">
</p>

---

## Tabla de contenidos

- [¿Para qué sirve en la vida real?](#para-qué-sirve-en-la-vida-real)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación rápida (5 minutos)](#instalación-rápida-5-minutos)
- [Instalación detallada](#instalación-detallada)
  - [1) Crear y activar entorno](#1-crear-y-activar-entorno)
  - [2) Instalar dependencias](#2-instalar-dependencias)
  - [3) Configurar el LLM (LM Studio local o endpoint online)](#3-configurar-el-llm-lm-studio-local-o-endpoint-online)
  - [4) Embeddings y RAG](#4-embeddings-y-rag)
  - [5) Ingesta de documentos](#5-ingesta-de-documentos)
  - [6) Levantar el servidor](#6-levantar-el-servidor)
- [Flujo de uso](#flujo-de-uso)
- [Variables de entorno (.env de ejemplo)](#variables-de-entorno-env-de-ejemplo)
- [Endpoints principales](#endpoints-principales)
- [Exportación](#exportación)
- [Ejecutar desde dispositivos modestos o móviles](#ejecutar-desde-dispositivos-modestos-o-móviles)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad y privacidad](#seguridad-y-privacidad)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Licencia y descargos](#licencia-y-descargos)

---

## ¿Para qué sirve en la vida real?

La **acción de tutela** es un **mecanismo constitucional** (art. 86) para la protección inmediata de **derechos fundamentales**. **No se requiere abogado** para interponerla: **cualquier persona** puede presentar su tutela. Puede amparar derechos **directamente** o por **conexidad** cuando un derecho no fundamental está íntimamente ligado a uno fundamental.

Este software permite que **cualquier persona** elabore, **presente y corrija** su tutela gracias a la **exportación a Word editable (.docx)** y a un **flujo guiado** que ordena hechos, pretensiones, pruebas y fundamentos. Al ejecutarse **en local**, con **bajos requisitos** (modelos pequeños como *Gemma 3/GEMA3* en LM Studio), favorece el **acceso a la justicia** en contextos con conectividad limitada o equipos modestos.

En la práctica, abogadas/os y ciudadanía enfrentan tres retos:
1. **Tiempo**: redactar bajo presión (plazos cortos).
2. **Calidad**: articular hechos, derechos y fundamentos jurídicos sin omitir piezas clave.
3. **Fuentes**: ubicar precedentes/referencias relevantes para el caso concreto.

Este proyecto ayuda a **estructurar** y **mejorar** el escrito de tutela, sugiere **derechos vulnerados**, arma **fundamentos jurídicos** (incluida una sección de **fundamentos de derecho vía RAG** con fuentes reales que cargues) y genera una **referencia (REF)** estandarizada. Todo con un flujo guiado, repetible y auditable.

**Ejes de Ciberpaz que inspiran esta hackatón (origen del programa):**
- **Derechos Digitales y Derechos de Autor**
- **Herramientas TIC para el trabajo incluyente y seguro**
- **Libertades Tecnológicas**
- **Diversidad e inclusión digital**
- **Seguridad y confianza digital**
- **Tecnología y Medio Ambiente**

> **Ejemplos de uso real**  
> - Personas a las que **no responden peticiones** en términos legales.  
> - **Demoras en entrega de tratamientos** o servicios de salud esenciales.  
> - **Barreras administrativas** que afectan derechos de niños, población vulnerable o trabajadores.  
> - Necesidad de **documentar pruebas y anexos** de manera clara y normalizada.


---

## Características

- **Wizard de Tutela** con flujo realista (usuario escribe; IA mejora).
- **RAG** con **Chroma** + embeddings HF para citar normas/sentencias (tú controlas el corpus).
- **Mejoras automáticas** al guardar en **Hechos**, **Pretensiones** (con sugerencias no‑económicas) y **Pruebas y Anexos**.
- **Cadena jurídica en un paso** (opcional):  
  `Hechos → Derechos vulnerados → Fundamentos jurídicos → Fundamentos de derecho (RAG) → REF`.
- **Secciones autocompletadas**: Intro, Notificaciones y Firmas desde datos de partes.
- **Persistencia** en **SQLite** (casos, partes, secciones, versiones).
- **Exportación** a **Word (.docx)** y **bundle .json** del caso.
- **Configurable por `.env`**.
- **Compatibilidad LLM local** (LM Studio; modelos pequeños tipo **Gemma 3/GEMA3**) y **funcionamiento online** contra un endpoint OpenAI‑compatible.

---

## Arquitectura

- **Backend:** FastAPI (endpoints `/advisor/*` y `/wizard/*`).
- **IA / LLM:** cualquier servidor **OpenAI‑compatible** (LM Studio recomendado para local).
- **RAG:** **ChromaDB** con embeddings de **Hugging Face** (p. ej., `intfloat/multilingual-e5-small`).
- **Archivos clave:**
  - `app.py` — enrutamiento y páginas rápidas.
  - `tutela.py` — lógica del Wizard (CRUD, mejoras IA, cadena, compose/export).
  - `advisor.py` — asesor jurídico con RAG (respuestas + citas).
  - `ingest.py` — ingesta de PDFs/DOCX/TXT/MD al índice vectorial.
  - `reset.py` — limpia el índice (`PERSIST_DIR`).

---

## Requisitos

- **Python** 3.10–3.12
- **Git** (opcional, para clonar)
- **LM Studio** (si usarás **LLM local**) o un **endpoint online** OpenAI‑compatible
- **Build tools** básicos (Windows: *Build Tools for Visual Studio* si alguna lib lo requiere)

---

## Instalación rápida (5 minutos)

```bash
# 1) Clonar (o copia local)
git clone https://github.com/tu-usuario/tu-repo-tutela.git
cd tu-repo-tutela

# 2) (opcional) Crear venv
python -m venv env
# Linux/macOS:
source env/bin/activate
# Windows (PowerShell):
.\env\Scripts\Activate.ps1

# 3) Instalar deps
pip install -r requirements.txt

# 4) Configurar .env (ver ejemplo abajo)

# 5) Ingestar tus fuentes (RAG)
python ingest.py

# 6) Levantar
uvicorn app:app --reload
```

Navega a: `http://127.0.0.1:8000` → páginas rápidas: **/tutela**, **/asesor**.

---

## Instalación detallada

### 1) Crear y activar entorno

```bash
python -m venv env
# Linux/macOS:
source env/bin/activate
# Windows:
.\env\Scripts\Activate.ps1
```

### 2) Instalar dependencias

Si aún no tienes `requirements.txt`, puedes generarlo con `pipreqs` o usar el provisto.  
Instala todo:

```bash
pip install -r requirements.txt
```

### 3) Configurar el LLM (LM Studio local o endpoint online)

**LM Studio (local):**
1. Abre LM Studio y descarga un modelo **pequeño** (ej.: *Gemma 3* en variante cuantil Q4/Q5).
2. Inicia el **Server** OpenAI‑compatible en `http://127.0.0.1:1234/v1`.
3. En tu `.env`:
   ```ini
   OPENAI_API_BASE=http://127.0.0.1:1234/v1
   OPENAI_API_KEY=lm-studio        # valor dummy aceptado por LM Studio
   LLM_MODEL=local/gemma-3         # etiqueta o nombre que uses en LM Studio
   LLM_TEMPERATURE=0.2
   ```

**Endpoint online (opcional):**  
Apunta `OPENAI_API_BASE` y `OPENAI_API_KEY` al proveedor remoto compatible, y define `LLM_MODEL` según su catálogo.

### 4) Embeddings y RAG

En `.env` puedes elegir embeddings (por defecto recomendados por su balance calidad/velocidad):

```ini
EMBEDDING_MODEL=intfloat/multilingual-e5-small
PERSIST_DIR=./chroma
TOP_K=3
DOCS_DIR=./docs
CHUNK_SIZE=600
```

### 5) Ingesta de documentos

Coloca tus **PDF/DOCX/TXT/MD** en `./docs` y corre:

```bash
python ingest.py
```

Para reiniciar desde cero:

```bash
python reset.py
python ingest.py
```

### 6) Levantar el servidor

```bash
uvicorn app:app --reload
```
- Salud: `GET /healthz`
- UI rápida: `/tutela` (wizard), `/asesor` (chat con RAG)

---

## Flujo de uso

1. **Crea un caso** en el Wizard.
2. **Registra partes** (accionantes/accionados) → el sistema arma **Intro**, **Notificaciones** y **Firmas**.
3. **Escribe Hechos / Pretensiones / Pruebas y Anexos** → al guardar, la IA **mejora** y normaliza.
4. Ejecuta la **cadena jurídica** (opcional en un paso):  
   **Derechos vulnerados → Fundamentos jurídicos → Fundamentos de derecho (RAG) → REF**.
5. **Compón** el texto final (endpoint de compose) o **exporta** a **.docx** y **.json**.
6. Revisa el **asesor** (/asesor) para dudas puntuales con **citas** de tu corpus.

---

## Variables de entorno (.env de ejemplo)

```ini
# === LLM local vía LM Studio ===
OPENAI_API_BASE=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
LLM_MODEL=local/gemma-3
LLM_TEMPERATURE=0.2

# === Salida del modelo ===
MAX_TOKENS_STEP=1024
LLM_MAX_TOKENS=4096

# === Embeddings (HuggingFace) ===
EMBEDDING_MODEL=intfloat/multilingual-e5-small

# === RAG (retrieval) ===
TOP_K=3

# === Vector DB (Chroma) ===
PERSIST_DIR=./chroma

# === Ingesta de documentos ===
DOCS_DIR=./docs
CHUNK_SIZE=600

# === Modo estricto del asesor (si no hay fuentes, no responde) ===
STRICT_CONTEXT=0
```

> **Nota:** si el proveedor remoto requiere otro nombre de modelo o token, ajusta `LLM_MODEL` y `OPENAI_API_KEY` según su documentación.

---

## Endpoints principales

- **Wizard**
  - `POST /wizard/case` — crea caso
  - `POST /wizard/case/{id}/party` — agrega/edita partes (auto: Intro/Notif/Firmas)
  - `POST /wizard/case/{id}/section/{name}` — guarda sección y mejora IA (según `name`)
  - `POST /wizard/case/{id}/run-pipeline` — ejecuta la cadena jurídica completa
  - `GET /wizard/case/{id}/compose-final` — devuelve texto final concatenado
  - `POST /wizard/case/{id}/export-docx` — genera `.docx` (y `.json` auxiliar)

- **Advisor (RAG)**
  - `POST /advisor/start` — inicia sesión de asesoría
  - `POST /advisor/answer` — responde con **citas** (y puntajes, si aplica)

---

## Exportación

- **DOCX**: formato jurídico (encabezado, títulos, numeraciones, bloque de firmas).
- **JSON**: bundle estructurado del caso para interoperabilidad (editores/servicios externos).

---

## Ejecutar desde dispositivos modestos o móviles

- **Hardware modesto**: con **LM Studio** + modelos **pequeños** (p. ej., *Gemma 3/GEMA3* cuantizada), el backend corre fluido en laptops de gama media/baja.
- **Acceso desde celular**: basta abrir la URL del servidor en el navegador del teléfono (misma red). El modelo puede correr:
  - **Local** en tu PC/mini‑PC (LM Studio) y el **celular solo consume la UI**.
  - **Online** en un servidor remoto OpenAI‑compatible (tu teléfono actúa como cliente).

> Ejecutar la **inferencia del LLM directamente en el teléfono** dependerá de apps/soporte específico. La vía simple: correr el LLM en un PC y usar el **celular como cliente**.

---

## Solución de problemas

**P1: `pipreqs` falla en Windows con `UnicodeDecodeError: 'charmap'`**  
Ejecuta forzando UTF‑8 y usa el ejecutable del venv:
```powershell
python -m pip install pipreqs==0.4.13
.\env\Scripts\pipreqs.exe . --force --savepath requirements.txt --encoding utf-8 --ignore "env,venv,.venv,.git,node_modules,docs,static,exports"
```

**P2: PowerShell no acepta `&&`**  
Usa `; if ($?) { ... }` o llama `cmd /c "comando1 && comando2"`.

**P3: LM Studio no responde**  
Verifica que el **Server** esté activo en `http://127.0.0.1:1234/v1` y que el modelo esté **cargado**. Ajusta `OPENAI_API_BASE` y `LLM_MODEL`.

**P4: No aparecen citas en Advisor**  
Asegúrate de haber corrido `python ingest.py` y que `DOCS_DIR` contenga documentos. Considera `STRICT_CONTEXT=1` para obligar respaldo documental.

---

## Seguridad y privacidad

- Tú controlas el **corpus** del RAG (`./docs`).
- Con **LLM local**, tus textos no salen de tu equipo. Con endpoint online, revisa términos del proveedor.
- Usa `STRICT_CONTEXT=1` si quieres bloquear respuestas sin fuentes en el índice.

---

## FAQ

**¿Necesito Internet?**  
No, si usas **LM Studio local** + tu corpus. Internet solo para descargar el modelo la primera vez.

**¿Puedo usar otro LLM?**  
Sí. Cualquier servidor **OpenAI‑compatible**. Ajusta `OPENAI_API_BASE`, `OPENAI_API_KEY` y `LLM_MODEL`.

**¿Qué documentos admite la ingesta?**  
PDF, DOCX, TXT y MD. Se trocean y se indexan en Chroma con metadatos de origen/página.

**¿Cómo reinicio el índice?**  
`python reset.py` y luego `python ingest.py`.

---

## Roadmap

- Validadores de consistencia entre **Hechos ←→ Pretensiones**.
- Plantillas DOCX personalizables por despacho/distrito.
- Panel de citas con **previsualización** (PDF.js) y export a **.bib**.
- Modo **colaborativo** (multiusuario) con autenticación.

---

## Licencia y descargos

Este software es **apoyo informativo** para la **redacción de tutelas**; **no sustituye** asesoría legal profesional. Úsalo bajo tu responsabilidad y valida siempre la normativa vigente y precedentes aplicables.  
Licencia: MIT (cámbiala si tu proyecto usa otra).

---

> ¿Sugerencia? Abre un **issue** o envía un **PR**. ¡Contribuciones bienvenidas!
