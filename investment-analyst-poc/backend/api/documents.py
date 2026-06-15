from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
from ..config import settings
from ..utils.logger import get_logger
from ..services.document_parser import DocumentParser
from ..services.blob_storage_service import BlobStorageService
from ..services.grounding_service import GroundingService
from ..services.session_lifecycle_service import SessionLifecycleService
from ..utils.db import init_db, record_file, record_session
import uuid

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    replace_session_id: Optional[str] = Form(None),
) -> JSONResponse:
    """Upload PDF/DOCX documents, persist them, and index them for analysis."""
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > settings.max_files_per_session:
        raise HTTPException(status_code=400, detail=f"Max {settings.max_files_per_session} files allowed")
    if session_id and replace_session_id:
        raise HTTPException(status_code=400, detail="Use either session_id or replace_session_id, not both")

    lifecycle = SessionLifecycleService()
    parser = DocumentParser()
    storage = BlobStorageService()
    grounding = GroundingService()
    created_new_session = not bool(session_id)
    active_session_id = session_id or await lifecycle.start_session(replace_session_id=replace_session_id)

    indexed_docs = []
    try:
        init_db()
        record_session(active_session_id, status="active")
        for f in files:
            fname = os.path.basename(f.filename or "uploaded")
            ext = os.path.splitext(fname)[1].lower()
            if ext not in [".pdf", ".docx"]:
                raise HTTPException(status_code=400, detail="Only PDF and DOCX supported")
            data = await f.read()
            if len(data) > settings.max_file_size_mb * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File too large (> {settings.max_file_size_mb}MB)")
            document_id = str(uuid.uuid4())
            stored = await storage.upload_bytes(
                session_id=active_session_id,
                document_id=document_id,
                file_name=fname,
                data=data,
                content_type=f.content_type,
            )
            source_uri = stored.get("blob_url") or stored.get("blob_name") or ""
            text = await parser.parse_bytes(fname, data)
            await grounding.index_document(
                session_id=active_session_id,
                document_id=document_id,
                source_name=fname,
                source_uri=source_uri,
                text=text,
            )
            record_file(
                active_session_id,
                fname,
                source_uri,
                document_id=document_id,
                storage_uri=source_uri,
                content_type=f.content_type or "",
            )
            indexed_docs.append(
                {
                    "name": fname,
                    "document_id": document_id,
                    "source_uri": source_uri,
                }
            )
        await grounding.persist()
    except Exception as e:
        logger.exception("Upload/index error")
        if created_new_session:
            try:
                await lifecycle.delete_session(active_session_id)
            except Exception:
                logger.exception("Failed cleaning up partially created session")
        raise HTTPException(status_code=500, detail=f"Failed to process files: {e}")

    return JSONResponse(
        {
            "session_id": active_session_id,
            "files": indexed_docs,
            "grounding_mode": grounding.mode,
        }
    )
