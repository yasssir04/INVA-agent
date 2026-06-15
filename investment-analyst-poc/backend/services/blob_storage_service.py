from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any, Dict

from ..config import settings


class BlobStorageService:
    """Stores session documents in Azure Blob Storage when cloud grounding is enabled."""

    def __init__(self) -> None:
        self._service_client = None

    @property
    def enabled(self) -> bool:
        return settings.grounding_mode == "azure_search"

    def _get_service_client(self):
        if self._service_client is None:
            if not settings.azure_storage_connection_string:
                raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required for azure_search mode")
            from azure.storage.blob import BlobServiceClient

            self._service_client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        return self._service_client

    def _session_prefix(self, session_id: str) -> str:
        prefix = settings.session_blob_prefix.strip("/")
        if prefix:
            return f"{prefix}/{session_id}/"
        return f"{session_id}/"

    def build_blob_name(self, session_id: str, document_id: str, file_name: str) -> str:
        safe_name = os.path.basename(file_name or "uploaded")
        return f"{self._session_prefix(session_id)}{document_id}/{safe_name}"

    async def ensure_container(self) -> None:
        if not self.enabled:
            return

        def _sync() -> None:
            container = self._get_service_client().get_container_client(settings.azure_storage_container)
            try:
                container.create_container()
            except Exception:
                pass

        await asyncio.to_thread(_sync)

    async def upload_bytes(
        self,
        session_id: str,
        document_id: str,
        file_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return await asyncio.to_thread(
                self._upload_local,
                session_id,
                document_id,
                file_name,
                data,
            )
        await self.ensure_container()
        blob_name = self.build_blob_name(session_id, document_id, file_name)

        def _sync() -> Dict[str, Any]:
            from azure.storage.blob import ContentSettings

            container = self._get_service_client().get_container_client(settings.azure_storage_container)
            blob = container.get_blob_client(blob_name)
            blob.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type or "application/octet-stream"),
            )
            return {
                "blob_name": blob_name,
                "blob_url": blob.url,
                "container": settings.azure_storage_container,
            }

        return await asyncio.to_thread(_sync)

    def _upload_local(
        self,
        session_id: str,
        document_id: str,
        file_name: str,
        data: bytes,
    ) -> Dict[str, Any]:
        safe_name = os.path.basename(file_name or "uploaded")
        dest_dir = os.path.join(settings.uploads_path, session_id, document_id)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, safe_name)
        with open(dest_path, "wb") as handle:
            handle.write(data)
        return {
            "blob_name": dest_path,
            "blob_url": dest_path,
            "container": "local",
        }

    async def delete_session_blobs(self, session_id: str) -> int:
        if not self.enabled:
            return await asyncio.to_thread(self._delete_local_session, session_id)
        await self.ensure_container()
        prefix = self._session_prefix(session_id)

        def _sync() -> int:
            container = self._get_service_client().get_container_client(settings.azure_storage_container)
            deleted = 0
            for item in container.list_blobs(name_starts_with=prefix):
                container.delete_blob(item.name)
                deleted += 1
            return deleted

        return await asyncio.to_thread(_sync)

    def _delete_local_session(self, session_id: str) -> int:
        session_dir = os.path.join(settings.uploads_path, session_id)
        if not os.path.isdir(session_dir):
            return 0
        count = 0
        for _, _, files in os.walk(session_dir):
            count += len(files)
        shutil.rmtree(session_dir, ignore_errors=True)
        return count