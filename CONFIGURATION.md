# Configuration

Use [.env.example](.env.example) as the template for your local `.env` file.

## Required secrets

- `AZURE_OPENAI_API_KEY`
- `TAVILY_API_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_SEARCH_API_KEY`

## Grounding modes

- `GROUNDING_MODE=azure_search`: uploads files to Azure Blob Storage, indexes chunks in Azure AI Search, and retrieves grounded evidence from Azure AI Search.
- `GROUNDING_MODE=faiss`: keeps the local fallback path for development and avoids Azure storage/search dependencies.

## Session cleanup behavior

- `AUTO_DELETE_ON_NEW_SESSION=true` deletes the previous session when a new upload replaces it.
- `POST /api/v1/sessions/reset` deletes the current session data.
- `DELETE /api/v1/sessions/{session_id}` deletes the current session data.

Cleanup removes:

- session metadata from SQLite
- session blobs from Azure Blob Storage when Azure mode is enabled
- session vectors/documents from Azure AI Search or local FAISS storage

## Public repo safety

- Do not commit `.env`.
- Rotate any key that has already been committed or shared.
- Keep production connection strings and API keys in your deployment environment, not in source control.
