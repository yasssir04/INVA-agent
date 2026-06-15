from __future__ import annotations

from typing import Any, Dict, List

from ..config import settings
from .azure_search_service import AzureSearchService
from .vector_store import VectorStore


class GroundingService:
    """Routes indexing, search, and deletion to the active grounding backend."""

    def __init__(self) -> None:
        self.mode = settings.grounding_mode
        self._search = AzureSearchService() if self.mode == "azure_search" else None
        self._vector_store = VectorStore(settings.faiss_index_path)

    async def index_document(
        self,
        session_id: str,
        document_id: str,
        source_name: str,
        source_uri: str,
        text: str,
    ) -> int:
        if self.mode == "azure_search":
            return await self._search.index_document(
                session_id=session_id,
                document_id=document_id,
                source_name=source_name,
                source_uri=source_uri,
                text=text,
            )
        return await self._vector_store.add_document_async(
            session_id=session_id,
            doc_path=source_uri or source_name,
            text=text,
            metadata={
                "document_id": document_id,
                "source_name": source_name,
                "source_uri": source_uri,
            },
        )

    async def search_evidence(self, session_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if self.mode == "azure_search":
            return await self._search.search(session_id=session_id, query=query, k=k)
        return await self._vector_store.search(session_id=session_id, query=query, k=k)

    async def delete_session(self, session_id: str) -> int:
        if self.mode == "azure_search":
            return await self._search.delete_session(session_id)
        return await self._vector_store.delete_session(session_id)

    async def persist(self) -> None:
        if self.mode == "faiss":
            self._vector_store.persist()