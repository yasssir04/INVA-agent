# Architecture Diagram

This file documents the current and target architectures for the Investment Analyst Agent.

## Architecture with local storage and FAISS

```mermaid
flowchart LR
    Analyst[Analyst] --> UI[Streamlit UI\napp.py]

    UI --> API[FastAPI Backend\nbackend/main.py]

    API --> Upload[Upload Endpoint\n/documents/upload]
    API --> Analyze[Analysis Endpoint\n/documents/analyze]
    API --> Opps[Opportunity Endpoint\n/opportunities/search]
    API --> Reports[Report Export Endpoints\n/reports/export/pdf and /reports/export/docx]

    Upload --> Parser[PDF and DOCX Parser]
    Parser --> Chunking[Chunking]
    Chunking --> Embeddings[Azure OpenAI Embeddings]
    Embeddings --> FAISS[Local FAISS Index]

    Analyze --> Kernel[Semantic Kernel Service]
    Kernel --> FAISS
    Kernel --> AOAI[Azure OpenAI GPT-4o]
    Kernel --> Memo[Investment Memo and Key Metrics]

    Opps --> Curated[Curated WebSummit Qatar Pages]
    Opps --> Tavily[Tavily Search]
    Tavily --> AOAI

    Reports --> UI
    Memo --> UI
```

## Architecture with Azure Blob Storage and Azure AI Search

```mermaid
flowchart LR
    Analyst[Analyst] --> UI[Streamlit UI\napp.py]

    UI --> API[FastAPI Backend\nbackend/main.py]

    API --> Upload[Document Intake]
    API --> Analyze[Grounded Analysis Request]
    API --> Opps[Opportunity Discovery]
    API --> Reports[Report Export]
    UI --> Reset[Delete or Reset Session]
    UI --> NewSession[Start New Session]

    Upload --> Blob[Azure Blob Storage\nSession Prefix]
    Upload --> Parse[Parse and Chunk Documents]
    Parse --> SearchIndex[Azure AI Search\nVector or Hybrid Index]

    Analyze --> Grounding[Grounding Service Abstraction]
    Grounding --> SearchIndex

    SearchIndex --> Evidence[Grounded Evidence and Citations\nFiltered by Session ID]
    Evidence --> Kernel[Semantic Kernel Orchestration]
    Kernel --> AOAI[Azure OpenAI GPT-4o]
    Kernel --> Results[Section Analysis, Scores, Memo, Citations]

    Results --> UI
    Results --> Reports

    Reset --> Cleanup[Session Cleanup Service]
    NewSession --> Cleanup
    Cleanup --> SearchIndex
    Cleanup --> Blob
    Cleanup --> SessionMeta[Session Metadata Cleanup]

    Opps --> Curated[Curated WebSummit Qatar Pages]
    Opps --> Tavily[Tavily Search]
    Tavily --> AOAI

    FAISSFallback[Optional Local FAISS Fallback for Dev Mode] -. optional .-> Grounding
```

## Key Difference

In the local-storage and FAISS architecture, the analysis path retrieves local chunks directly from FAISS.

In the Azure Blob Storage and Azure AI Search architecture, uploaded files are stored in Azure Blob Storage, parsed and chunked by the backend, indexed in Azure AI Search, and then used to ground the analyst agent with session-filtered evidence and citations.

Both architectures treat deletion as part of the core design: reset, delete, and new-session events remove the old session's blobs, search records, and metadata.
