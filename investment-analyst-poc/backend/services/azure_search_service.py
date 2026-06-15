from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from openai import AsyncAzureOpenAI

from ..config import settings
from ..utils.helpers import chunk_text


class AzureSearchService:
    """Manages an Azure AI Search vector index for session-grounded retrieval."""

    def __init__(self) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        self._index_ready = False

    def _assert_config(self) -> None:
        if not settings.azure_search_endpoint:
            raise RuntimeError("AZURE_SEARCH_ENDPOINT is required for azure_search mode")
        if not settings.azure_search_api_key:
            raise RuntimeError("AZURE_SEARCH_API_KEY is required for azure_search mode")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": settings.azure_search_api_key,
        }

    def _index_url(self) -> str:
        return (
            f"{settings.azure_search_endpoint}/indexes/{settings.azure_search_index_name}"
            f"?api-version={settings.azure_search_api_version}"
        )

    def _docs_search_url(self) -> str:
        return (
            f"{settings.azure_search_endpoint}/indexes/{settings.azure_search_index_name}/docs/search"
            f"?api-version={settings.azure_search_api_version}"
        )

    def _docs_index_url(self) -> str:
        return (
            f"{settings.azure_search_endpoint}/indexes/{settings.azure_search_index_name}/docs/index"
            f"?api-version={settings.azure_search_api_version}"
        )

    def _hash(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]

    def _build_index_schema(self) -> Dict[str, Any]:
        return {
            "name": settings.azure_search_index_name,
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
                {"name": "session_id", "type": "Edm.String", "filterable": True, "sortable": True},
                {"name": "document_id", "type": "Edm.String", "filterable": True},
                {"name": "source_name", "type": "Edm.String", "searchable": True},
                {"name": "source_uri", "type": "Edm.String"},
                {"name": "chunk_id", "type": "Edm.String", "filterable": True},
                {"name": "chunk_order", "type": "Edm.Int32", "filterable": True, "sortable": True},
                {"name": "chunk_text", "type": "Edm.String", "searchable": True},
                {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
                {
                    "name": "embedding",
                    "type": "Collection(Edm.Single)",
                    "searchable": True,
                    "dimensions": settings.azure_search_vector_dimensions,
                    "vectorSearchProfile": "default-vector-profile",
                },
            ],
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "default-hnsw",
                        "kind": "hnsw",
                        "hnswParameters": {"metric": "cosine"},
                    }
                ],
                "profiles": [
                    {
                        "name": "default-vector-profile",
                        "algorithm": "default-hnsw",
                    }
                ],
            },
        }

    def _request(self, method: str, url: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        response = requests.request(method, url, headers=self._headers(), json=payload, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(f"Azure AI Search request failed ({response.status_code}): {response.text}")
        if not response.text:
            return {}
        return response.json()

    async def ensure_index(self) -> None:
        if self._index_ready:
            return

        def _sync() -> None:
            self._assert_config()
            probe = requests.get(self._index_url(), headers=self._headers(), timeout=30)
            if probe.status_code == 200:
                return
            if probe.status_code != 404:
                raise RuntimeError(
                    f"Azure AI Search index probe failed ({probe.status_code}): {probe.text}"
                )
            self._request("PUT", self._index_url(), self._build_index_schema())

        await asyncio.to_thread(_sync)
        self._index_ready = True

    async def _embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=settings.azure_openai_deployment_embedding,
            input=texts,
        )
        return [list(map(float, item.embedding)) for item in response.data]

    async def index_document(
        self,
        session_id: str,
        document_id: str,
        source_name: str,
        source_uri: str,
        text: str,
    ) -> int:
        await self.ensure_index()
        chunks = chunk_text(text)
        if not chunks:
            return 0
        embeddings = await self._embed(chunks)
        created_at = datetime.now(timezone.utc).isoformat()
        actions = []
        for idx, chunk in enumerate(chunks):
            actions.append(
                {
                    "@search.action": "mergeOrUpload",
                    "id": self._hash(f"{session_id}:{document_id}:{idx}"),
                    "session_id": session_id,
                    "document_id": document_id,
                    "source_name": source_name,
                    "source_uri": source_uri,
                    "chunk_id": f"{document_id}:{idx}",
                    "chunk_order": idx,
                    "chunk_text": chunk,
                    "created_at": created_at,
                    "embedding": embeddings[idx],
                }
            )

        def _sync() -> None:
            self._request("POST", self._docs_index_url(), {"value": actions})

        await asyncio.to_thread(_sync)
        return len(actions)

    async def search(self, session_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        await self.ensure_index()
        vectors = await self._embed([query])
        filter_session = session_id.replace("'", "''")
        payload: Dict[str, Any] = {
            "search": query,
            "filter": f"session_id eq '{filter_session}'",
            "top": k,
            "select": "id,session_id,document_id,source_name,source_uri,chunk_id,chunk_order,chunk_text,created_at",
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": vectors[0],
                    "fields": "embedding",
                    "k": max(k * 3, k),
                }
            ],
        }

        def _sync_search() -> Dict[str, Any]:
            try:
                return self._request("POST", self._docs_search_url(), payload)
            except RuntimeError:
                fallback = dict(payload)
                fallback.pop("vectorQueries", None)
                return self._request("POST", self._docs_search_url(), fallback)

        response = await asyncio.to_thread(_sync_search)
        items = response.get("value", []) or []
        return [
            {
                "id": item.get("id", ""),
                "session_id": item.get("session_id", session_id),
                "document_id": item.get("document_id", ""),
                "source_name": item.get("source_name") or "Document",
                "source_uri": item.get("source_uri", ""),
                "citation_id": item.get("chunk_id") or item.get("id", ""),
                "text": item.get("chunk_text", ""),
                "metadata": {
                    "chunk_order": item.get("chunk_order", 0),
                    "created_at": item.get("created_at", ""),
                },
            }
            for item in items
        ]

    async def delete_session(self, session_id: str) -> int:
        await self.ensure_index()
        filter_session = session_id.replace("'", "''")

        def _sync_delete() -> int:
            deleted = 0
            while True:
                found = self._request(
                    "POST",
                    self._docs_search_url(),
                    {
                        "search": "*",
                        "filter": f"session_id eq '{filter_session}'",
                        "top": 1000,
                        "select": "id",
                    },
                )
                ids = [item.get("id") for item in (found.get("value") or []) if item.get("id")]
                if not ids:
                    break
                actions = [{"@search.action": "delete", "id": item_id} for item_id in ids]
                self._request("POST", self._docs_index_url(), {"value": actions})
                deleted += len(actions)
                if len(ids) < 1000:
                    break
            return deleted

        return await asyncio.to_thread(_sync_delete)