from __future__ import annotations
import os
import json
import hashlib
from typing import Any, Dict, List
import numpy as np
import faiss
from openai import AsyncAzureOpenAI
from ..config import settings
from ..utils.logger import get_logger
from ..utils.helpers import chunk_text

logger = get_logger(__name__)


class VectorStore:
    """FAISS-based vector store with OpenAI embeddings."""

    def __init__(self, index_dir: str) -> None:
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        self.index_path = os.path.join(index_dir, "index.faiss")
        self.meta_path = os.path.join(index_dir, "meta.json")
        self.dim = 1536  # text-embedding-ada-002
        self.index = faiss.IndexFlatIP(self.dim)
        self.meta: List[Dict[str, Any]] = []
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.meta = json.load(f)

    def persist(self) -> None:
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f)

    async def _embed(self, texts: List[str]) -> np.ndarray:
        # Using Azure OpenAI embeddings endpoint compatible with OpenAI SDK v2
        res = await self._client.embeddings.create(
            model=settings.azure_openai_deployment_embedding,
            input=texts,
        )
        vecs = np.array([d.embedding for d in res.data], dtype=np.float32)
        # Normalize for inner product similarity
        faiss.normalize_L2(vecs)
        return vecs

    def _hash(self, s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    async def add_document_async(
        self,
        session_id: str,
        doc_path: str,
        text: str,
        metadata: Dict[str, Any] | None = None,
    ) -> int:
        metadata = metadata or {}
        chunks = chunk_text(text)
        if not chunks:
            return 0
        ids = [self._hash(f"{session_id}:{doc_path}:{i}") for i in range(len(chunks))]
        vecs = await self._embed(chunks)
        self.index.add(vecs)
        for i, ch in enumerate(chunks):
            self.meta.append({
                "id": ids[i],
                "session_id": session_id,
                "document_id": metadata.get("document_id", ""),
                "doc_path": doc_path,
                "source_name": metadata.get("source_name") or os.path.basename(doc_path) or "Document",
                "source_uri": metadata.get("source_uri") or doc_path,
                "chunk_id": ids[i],
                "chunk_order": i,
                "text": ch,
            })
        return len(chunks)

    async def search(self, session_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not self.meta:
            return []
        # Simple keyword pre-filter
        q_words = set([w.lower() for w in query.split() if len(w) > 2])
        candidate_idxs = [i for i, m in enumerate(self.meta) if m.get("session_id") == session_id and any(w in m.get("text", "").lower() for w in q_words)]
        if not candidate_idxs:
            candidate_idxs = [i for i, m in enumerate(self.meta) if m.get("session_id") == session_id]
        if not candidate_idxs:
            return []

        # Semantic rerank
        qv = await self._embed([query])
        # Search entire index (POC) and then filter by session
        D, I = self.index.search(qv, min(k * 10, len(self.meta)))
        results: List[Dict[str, Any]] = []
        for idx in I[0]:
            if idx < 0 or idx >= len(self.meta):
                continue
            m = self.meta[idx]
            if m.get("session_id") == session_id:
                results.append({
                    "id": m.get("id", ""),
                    "session_id": session_id,
                    "document_id": m.get("document_id", ""),
                    "source_name": m.get("source_name") or os.path.basename(m.get("doc_path", "")) or "Document",
                    "source_uri": m.get("source_uri") or m.get("doc_path", ""),
                    "citation_id": m.get("chunk_id") or m.get("id", ""),
                    "text": m.get("text", ""),
                    "metadata": {
                        "chunk_order": m.get("chunk_order", 0),
                    },
                })
            if len(results) >= k:
                break
        return results

    async def delete_session(self, session_id: str) -> int:
        if not self.meta:
            return 0
        keep_meta: List[Dict[str, Any]] = []
        keep_indices: List[int] = []
        removed = 0
        for idx, item in enumerate(self.meta):
            if item.get("session_id") == session_id:
                removed += 1
                continue
            keep_meta.append(item)
            keep_indices.append(idx)
        if removed == 0:
            return 0
        new_index = faiss.IndexFlatIP(self.dim)
        if keep_indices:
            vectors = np.vstack([self.index.reconstruct(int(i)) for i in keep_indices]).astype(np.float32)
            new_index.add(vectors)
        self.index = new_index
        self.meta = keep_meta
        self.persist()
        return removed
