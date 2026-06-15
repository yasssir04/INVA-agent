from __future__ import annotations

import uuid

from ..config import settings
from ..utils.db import delete_session_records, init_db, record_session, update_session_status
from ..utils.logger import get_logger
from .blob_storage_service import BlobStorageService
from .grounding_service import GroundingService

logger = get_logger(__name__)


class SessionLifecycleService:
    """Creates, resets, and deletes session-scoped resources."""

    def __init__(self) -> None:
        self.storage = BlobStorageService()
        self.grounding = GroundingService()
        init_db()

    async def start_session(self, replace_session_id: str | None = None) -> str:
        if replace_session_id and settings.auto_delete_on_new_session:
            await self.delete_session(replace_session_id)
        session_id = str(uuid.uuid4())
        record_session(session_id, status="active")
        return session_id

    async def reset_session(self, session_id: str) -> None:
        await self.delete_session(session_id)

    async def delete_session(self, session_id: str) -> None:
        if not session_id:
            return
        update_session_status(session_id, "deleting")
        errors: list[str] = []

        try:
            await self.grounding.delete_session(session_id)
        except Exception as exc:
            logger.exception("Failed cleaning up index state for session %s", session_id)
            errors.append(f"index cleanup failed: {exc}")

        try:
            await self.storage.delete_session_blobs(session_id)
        except Exception as exc:
            logger.exception("Failed cleaning up stored files for session %s", session_id)
            errors.append(f"blob cleanup failed: {exc}")

        if errors:
            update_session_status(session_id, "delete_error")
            raise RuntimeError("; ".join(errors))

        delete_session_records(session_id)