# INVA Agent – AI Investment Analyst

> Submission for Microsoft Agents League @ AI Skills Fest – reasoning‑heavy, document‑grounded investment analyst agent for VC/PE teams.

INVA Agent (AI Investment Analyst) is a Streamlit + FastAPI app that acts as a junior investment analyst for two workflows:

1. **Document‑grounded investment analysis** on uploaded PDF/DOCX files  
2. **Qatar startup opportunity discovery** using curated Web Summit pages plus AI ranking

The app demonstrates a full RAG + multi‑step reasoning pipeline on Azure, built to be easy to run locally but architected like a real product POC.

---

## Why this problem exists now

AI is no longer a niche segment in venture; it is the centre of gravity.

Recent analyses show that AI startups went from representing about **27.5% of global VC deal value in 2023** to **40% in 2024** and **52.7% in 2025**—for the first time, more VC dollars went to AI startups than to every other sector combined. PitchBook‑ and Crunchbase‑based reports estimate that **AI‑related startups attracted around \$200–270B in 2025**, with AI capturing roughly **half of all global VC funding** and as much as **57–64% of VC value in some quarters and in the U.S.**.

At the same time, the **number of newly funded AI companies has spiked**: Stanford’s AI Index and follow‑on analyses highlight **1,800+ newly funded AI companies in a single year**, with later data showing **over 2,000 AI startups receiving fresh funding in 2024**, and more than **half a trillion dollars of private capital** flowing into AI over the last decade. This surge reflects how better AI tooling lowers the barrier to launching AI‑native products, directly fuelling new startup creation.

For VC and PE teams, this creates a paradox: AI amplifies deal sourcing and data (deck parsing, auto‑sourcing, benchmarking), but human analyst capacity has not scaled at the same rate. Analysts and associates are expected to triage thousands of AI‑heavy opportunities, run first‑pass diligence, and produce credible memos under tight time pressure with lean teams.

**INVA Agent (AI Investment Analyst)** is an investment‑analyst agent designed for VC/PE analysts and associates who need to complete fast, high‑quality first‑pass diligence with lean teams and overwhelming volumes of startup information—generating a grounded, evidence‑linked investment memo in **under 60 seconds**.

---

## What this agent does

INVA Agent focuses on **fast, grounded first‑pass diligence**, not automated investment decisions:

- Upload up to **4 PDF/DOCX investment documents** (pitch decks, one‑pagers, financials) per session.
- Run **document‑grounded scoring** (0–100) across key investment metrics, with confidence estimates and citations.
- Generate a structured **investment memo** that links every key claim back to evidence in the uploaded documents.
- Export **PDF and DOCX reports** for the current session for sharing within the deal team.
- **Discover and rank Qatar startups** in a chosen sector using curated Web Summit Qatar pages plus Tavily‑enriched web context.
- Reset/delete sessions to clean up all stored blobs, vectors, and metadata (local or Azure), aligning with responsible data handling.

---

## High‑level architecture

The app is built as a two‑tier web application:

- **Frontend:** Streamlit (`app.py`) for the analyst UI.
- **Backend:** FastAPI (`backend/main.py`) exposing APIs for upload, analysis, sessions, and opportunity discovery.

It supports two grounding modes:

- `GROUNDING_MODE=azure_search` – production‑style RAG with **Azure Blob Storage + Azure AI Search**.
- `GROUNDING_MODE=faiss` – local **FAISS** index for development or offline demos.

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
   **Semantic Kernel + Azure OpenAI** generate grounded, section‑by‑section analysis and memos, injecting retrieved evidence and returning citations.

7. **Export**  
   The user can export grounded reports as **PDF or DOCX**, preserving scores, analysis, and citations.

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

In this **v1**, INVA Agent focuses on the **Qatar market** for startup opportunity discovery, using curated Web Summit Qatar startup pages as the primary source of candidates. The same pattern can be extended in future versions to a **global startup graph** by swapping or augmenting the Qatar corpus with other ecosystems (e.g., additional conference lists, accelerator portfolios, or structured startup data platforms).

Reasoning steps:

1. **Sector selection** – user selects a target sector (e.g., fintech, health, climate).  
2. **Candidate fetch** – the backend pulls startups from curated Web Summit Qatar pages and related Qatar startup sources.[web:137][web:141][web:145]  
3. **Context enrichment** – for each candidate, the app gathers compact web context with **Tavily**.  
4. **AI scoring** – **Azure OpenAI** scores and ranks startups based on opportunity fit, differentiation, and traction.  
5. **Ranked output** – the top opportunities are returned with explanations and confidence scores.

This showcases **multi‑source reasoning** (curated data + live web) for a real regional use case today, with a clear path to global coverage in future iterations.

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
- The Azure path parses from the upload payload rather than Blob to avoid extra I/O, but this can be revisited for very large files.  
- The repo still needs `git init` before being published as a clean public project.

Possible future improvements:

- Add OCR for scanned PDFs.  
- Move vectors and metadata into a single production‑grade store.  
- Add more structured outputs via Semantic Kernel function‑calling.  
- Add tests (unit + smoke) and CI for more robust deployments.  
- Generalise startup discovery from Qatar‑only to a **global multi‑region startup graph**.

---

## Public repo / contest checklist

- Ensure `.env` is **never committed**.  
- Use the existing [.gitignore](.gitignore).  
- Keep [CONFIGURATION.md](CONFIGURATION.md) for secret‑safe setup guidance.  
- Use [architecture-diagram.md](architecture-diagram.md) to communicate the target architecture.  
- Add screenshots or a short demo video link for contest submissions.
