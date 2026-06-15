# AI Investment Analyst POC

AI Investment Analyst is a Streamlit plus FastAPI application for two workflows:

1. document-grounded investment analysis for uploaded PDF and DOCX files
2. Qatar startup opportunity discovery using curated WebSummit pages and AI ranking

The document-analysis path now supports two grounding modes:

- `GROUNDING_MODE=azure_search`: store uploaded files in Azure Blob Storage, index parsed chunks in Azure AI Search, and ground the analyst on Azure AI Search results filtered to the active session
- `GROUNDING_MODE=faiss`: keep the local fallback path for development using local uploads plus FAISS

## Current backend flow

In `azure_search` mode, the backend logic is:

1. the uploaded document is stored in Azure Blob Storage
2. the backend parses the uploaded bytes and chunks the extracted text
3. the chunks are embedded with Azure OpenAI and indexed into Azure AI Search with session metadata and source URI
4. the analyst agent retrieves grounded evidence from Azure AI Search for the active session
5. the grounded evidence is injected into the analysis prompts and returned with citations

Important nuance: the current implementation stores the file in Blob first, but parsing is still done from the uploaded bytes already in memory, not by downloading the file back from Blob. So the effective flow is Blob first, then Azure AI Search indexing, then grounded analysis.

## What you can do

- Upload up to 4 PDF or DOCX files per session
- Generate section-by-section investment analysis with scores and confidence
- View a dashboard with weighted 0 to 100 key metrics
- Generate an investment memo
- Export PDF and DOCX reports with citations
- Reset or delete a session and remove its stored data
- Discover Qatar startup opportunities with AI scoring

## Document analysis architecture

### Azure grounding mode

When `GROUNDING_MODE=azure_search`:

1. Streamlit uploads files to the FastAPI backend
2. the backend stores each file in Azure Blob Storage
3. the backend parses PDF or DOCX content
4. the backend chunks the text and creates embeddings with Azure OpenAI
5. the backend writes chunk records into Azure AI Search
6. the analyst retrieves session-filtered evidence from Azure AI Search
7. Semantic Kernel plus Azure OpenAI generates grounded analysis and memo output
8. exports include the grounded text and citations

### Local fallback mode

When `GROUNDING_MODE=faiss`:

1. files are stored locally
2. parsed chunks are embedded and stored in FAISS
3. retrieval is served from the local FAISS index

## Session lifecycle and deletion

The app now treats uploaded documents as session-scoped data.

Deletion paths:

- `POST /api/v1/sessions/reset` deletes the current session data
- `DELETE /api/v1/sessions/{session_id}` deletes the current session data
- uploading a new batch with an existing session triggers replacement behavior when `AUTO_DELETE_ON_NEW_SESSION=true`

Cleanup removes:

- session metadata from SQLite
- session blobs from Azure Blob Storage in Azure mode
- session records from Azure AI Search in Azure mode
- session vectors from FAISS in local mode

## Opportunity discovery flow

The Qatar opportunity-discovery flow is unchanged.

1. select a sector
2. fetch candidate startups from curated WebSummit Qatar pages
3. gather compact web context with Tavily
4. score candidates with Azure OpenAI
5. return the top ranked opportunities with explanation and confidence

## Main components

- [app.py](app.py): Streamlit frontend
- [backend/main.py](backend/main.py): FastAPI app and router registration
- [backend/api/documents.py](backend/api/documents.py): upload and indexing flow
- [backend/api/analysis.py](backend/api/analysis.py): grounded analysis endpoint
- [backend/api/sessions.py](backend/api/sessions.py): session reset and delete APIs
- [backend/services/blob_storage_service.py](backend/services/blob_storage_service.py): Azure Blob Storage integration
- [backend/services/azure_search_service.py](backend/services/azure_search_service.py): Azure AI Search indexing and retrieval
- [backend/services/grounding_service.py](backend/services/grounding_service.py): routing between Azure Search and FAISS
- [backend/services/semantic_kernel_service.py](backend/services/semantic_kernel_service.py): grounded analyst orchestration

## Setup

### Prerequisites

- Python 3.11+
- Azure OpenAI resource and deployments
- Tavily API key
- Azure Blob Storage connection string for Azure grounding mode
- Azure AI Search service and admin key for Azure grounding mode

### Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
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
- `GROUNDING_MODE`
- `AUTO_DELETE_ON_NEW_SESSION`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_CONTAINER`
- `SESSION_BLOB_PREFIX`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`
- `AZURE_SEARCH_API_VERSION`
- `AZURE_SEARCH_VECTOR_DIMENSIONS`

### Run

Backend:

```powershell
uvicorn backend.main:app --app-dir . --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
streamlit run app.py
```

## Notes for contest/public repo use

- `.env` should stay uncommitted
- use [.gitignore](.gitignore)
- use [CONFIGURATION.md](CONFIGURATION.md) for secret-safe setup guidance
- [architecture-diagram.md](architecture-diagram.md) documents the target architecture
- [plan.md](plan.md) captures the migration plan and differences

## Known limitations

- scanned or image-only PDFs are still not OCR-enabled
- report export currently re-runs analysis for the session before generating the file
- the Azure path stores to Blob first, but parsing still happens from the upload payload already in memory
- the repo folder still needs `git init` before it can be published cleanly

## Public repo checklist

- confirm `.env` is not committed
- rotate any secret that was ever stored in the repo or shared outside a secure environment
- initialize git before publishing this folder
- add screenshots or a short demo video link if this will be used for a contest submission
