# AI Investment Analyst – Agents League Edition

> Submission for Microsoft Agents League @ AI Skills Fest – Reasoning‑heavy, document‑grounded investment analysis with Qatar startup scouting in v1(global market in future).

AI Investment Analyst is a Streamlit + FastAPI app that acts as an AI “junior analyst” for two workflows:

1. **Document‑grounded investment analysis** on uploaded PDF/DOCX files  
2. **Qatar startup opportunity discovery** using curated WebSummit pages plus AI ranking

The app demonstrates a full RAG + multi‑step reasoning pipeline on Azure, built to be easy to run locally but architected like a real product POC.[memory:95]

---

## Why this project

Traditional investment analysis workflows are slow and manual:

- Analysts read long pitch decks and financials, then write memos from scratch.
- Regional opportunities (e.g., Qatar startups) are scattered across multiple websites.
- It is hard to compare opportunities consistently and keep track of evidence.

**AI Investment Analyst** addresses this by:

- Turning uploaded investment documents into **grounded, section‑by‑section analysis with scores, confidence, and citations**.
- Discovering **Qatar startups in selected sectors**, enriching them with web context, and ranking them with AI.
- Providing a **transparent, session‑scoped workflow** with explicit cleanup and deletion.

---

## Key capabilities (for judges and reviewers)

- Upload up to **4 PDF/DOCX documents** per session for investment analysis.
- Run **document‑grounded scoring** (0–100) across key investment metrics, with confidence estimates and citations.
- Generate a structured **investment memo** that links back to the underlying evidence.
- Export **PDF and DOCX reports** for the current session.
- **Discover and rank Qatar startups** in a chosen sector using curated WebSummit pages + Tavily search.
- Reset/delete sessions to clean up all stored blobs, vectors, and metadata (local or Azure).

---

## High‑level architecture

The app is built as a two‑tier web application:

- **Frontend:** Streamlit (`app.py`) for the analyst UI.
- **Backend:** FastAPI (`backend/main.py`) exposing APIs for upload, analysis, sessions, and opportunity discovery.

It supports two grounding modes:

- `GROUNDING_MODE=azure_search` – production‑style RAG with Azure Blob Storage + Azure AI Search.
- `GROUNDING_MODE=faiss` – local FAISS index for development or offline demos.

### Azure grounding mode (`GROUNDING_MODE=azure_search`)

End‑to‑end reasoning flow:

1. **Upload**  
   Streamlit uploads one or more PDF/DOCX files to the FastAPI backend.

2. **Persist**  
   The backend stores each file in **Azure Blob Storage**.

3. **Parse & chunk**  
   The backend parses the uploaded bytes, extracts text, and chunks it into embedding‑friendly segments.

4. **Embed & index**  
   Chunks are embedded with **Azure OpenAI** and written into **Azure AI Search** along with session metadata and a source URI.

5. **Retrieve evidence**  
   For each analysis request, the analyst agent queries Azure AI Search with a **session filter** to retrieve only the current user’s evidence.

6. **Reason & generate**  
   **Semantic Kernel + Azure OpenAI** generate grounded analysis and memos, injecting retrieved evidence and returning citations.

7. **Export**  
   The user can export grounded reports as PDF or DOCX, preserving scores, analysis, and citations.

> Note: Files are stored in Blob first, but parsing uses the in‑memory upload payload to avoid extra round‑trips.

### Local fallback mode (`GROUNDING_MODE=faiss`)

For local development or no‑Azure environments:

1. Files are stored locally.  
2. Parsed chunks are embedded and stored in **FAISS**.  
3. Retrieval queries the local FAISS index instead of Azure AI Search.

---

## Session lifecycle, privacy, and deletion

Uploaded documents are treated as **session‑scoped** data so that evidence and analysis are always tied to a specific session.

Session management endpoints:

- `POST /api/v1/sessions/reset` – reset the current session.
- `DELETE /api/v1/sessions/{session_id}` – hard‑delete a session by ID.
- `AUTO_DELETE_ON_NEW_SESSION=true` – automatically replace old session data when a new batch is uploaded.

Cleanup actions:

- Remove session metadata from **SQLite**.
- Delete session blobs from **Azure Blob Storage** (Azure mode).
- Delete session records from **Azure AI Search** (Azure mode).
- Delete session vectors from **FAISS** (local mode).

This makes it straightforward to demonstrate **responsible data handling** and “clean teardown” during hackathon judging.

---

## Qatar opportunity discovery flow

The Qatar startup discovery flow uses curated WebSummit Qatar pages plus lightweight web search to surface and rank opportunities.

Reasoning steps:

1. **Sector selection** – user selects a target sector (e.g., fintech, health, climate).  
2. **Candidate fetch** – the backend pulls startups from curated WebSummit Qatar pages.  
3. **Context enrichment** – for each candidate, the app gathers compact web context with **Tavily**.  
4. **AI scoring** – **Azure OpenAI** scores and ranks startups based on opportunity fit, differentiation, and traction.  
5. **Ranked output** – the top opportunities are returned with explanations and confidence scores.

This showcases **multi‑source reasoning** (curated data + live web) for a real regional use case.

---

## Main components

- [`app.py`](app.py) – Streamlit UI, upload forms, dashboards, and report actions.
- [`backend/main.py`](backend/main.py) – FastAPI app and router registration.
- [`backend/api/documents.py`](backend/api/documents.py) – upload, parsing, chunking, and indexing flow.
- [`backend/api/analysis.py`](backend/api/analysis.py) – grounded analysis and memo generation endpoints.
- [`backend/api/sessions.py`](backend/api/sessions.py) – session lifecycle (reset, delete).
- [`backend/services/blob_storage_service.py`](backend/services/blob_storage_service.py) – Azure Blob Storage integration.
- [`backend/services/azure_search_service.py`](backend/services/azure_search_service.py) – Azure AI Search indexing and retrieval.
- [`backend/services/grounding_service.py`](backend/services/grounding_service.py) – routing between Azure Search and FAISS.
- [`backend/services/semantic_kernel_service.py`](backend/services/semantic_kernel_service.py) – Semantic Kernel orchestration for grounded analysis.

---

## Getting started

### Prerequisites

- Python **3.11+**
- **Azure OpenAI** resource and deployments (GPT‑4o + embeddings)
- **Tavily** API key
- **Azure Blob Storage** account (for Azure grounding mode)
- **Azure AI Search** service (for Azure grounding mode)

### Install

```bash
python -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

### Configure

Use [.env.example](.env.example) as the template for your local `.env`.

Important variables:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT_GPT4O`
- `AZURE_OPENAI_DEPLOYMENT_EMBEDDING`
- `AZURE_OPENAI_API_VERSION`
- `TAVILY_API_KEY`
- `GROUNDING_MODE` (`azure_search` or `faiss`)
- `AUTO_DELETE_ON_NEW_SESSION`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_CONTAINER`
- `SESSION_BLOB_PREFIX`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`
- `AZURE_SEARCH_API_VERSION`
- `AZURE_SEARCH_VECTOR_DIMENSIONS`

### Run locally

Backend:

```bash
uvicorn backend.main:app --app-dir . --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
streamlit run app.py
```

Then open the Streamlit URL shown in your terminal.

---

## Suggested demo flow (for hackathon judges)

1. **Upload 1–4 investment PDFs** (pitch deck, financials, or example docs).  
2. Run **document analysis** → show section‑wise scores, confidence, and citations.  
3. Generate an **investment memo** → point out how it references grounded evidence.  
4. Export **PDF/DOCX** → emphasise that the reports are reproducible and shareable.  
5. Switch to **Qatar startup discovery**, pick a sector, and show ranked startups with explanations.  
6. Reset or delete the session → highlight privacy and cleanup behaviour.

---

## Known limitations & future work

- OCR is not yet enabled for scanned/image‑only PDFs.  
- Report export re‑runs analysis for the current session before generating files.  
- Azure path parses from the upload payload rather than Blob to avoid extra I/O, but this can be revisited for very large files.  
- The repo still needs `git init` before being published as a clean public project.

Possible future improvements:

- Add OCR for scanned PDFs.  
- Move vectors and metadata into a single production‑grade store.  
- Add more structured outputs via Semantic Kernel function‑calling.  
- Add tests (unit + smoke) and CI for more robust deployments.

---

## Public repo / contest checklist

- Ensure `.env` is **never committed**.  
- Use the existing [.gitignore](.gitignore).  
- Keep [CONFIGURATION.md](CONFIGURATION.md) for secret‑safe setup guidance.  
- Use [architecture-diagram.md](architecture-diagram.md) to communicate the target architecture.  
- Add screenshots or a short demo video link for contest submissions.
