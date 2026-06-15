from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..services.session_lifecycle_service import SessionLifecycleService
from ..utils.logger import get_logger

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = get_logger(__name__)


class StartSessionRequest(BaseModel):
    replace_session_id: Optional[str] = None


class SessionRequest(BaseModel):
    session_id: str = Field(..., min_length=8)


@router.post("/start")
async def start_session(payload: Optional[StartSessionRequest] = None) -> JSONResponse:
    try:
        lifecycle = SessionLifecycleService()
        session_id = await lifecycle.start_session(
            replace_session_id=payload.replace_session_id if payload else None
        )
        return JSONResponse({"session_id": session_id, "status": "active"})
    except Exception as e:
        logger.exception("Start session error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(payload: SessionRequest) -> JSONResponse:
    try:
        lifecycle = SessionLifecycleService()
        await lifecycle.reset_session(payload.session_id)
        return JSONResponse({"session_id": payload.session_id, "status": "reset"})
    except Exception as e:
        logger.exception("Reset session error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> JSONResponse:
    try:
        lifecycle = SessionLifecycleService()
        await lifecycle.delete_session(session_id)
        return JSONResponse({"session_id": session_id, "status": "deleted"})
    except Exception as e:
        logger.exception("Delete session error")
        raise HTTPException(status_code=500, detail=str(e))