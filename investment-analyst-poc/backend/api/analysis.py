from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any
from ..utils.logger import get_logger
from ..services.semantic_kernel_service import KernelService

router = APIRouter(prefix="/documents", tags=["analysis"]) 
logger = get_logger(__name__)


class AnalyzeRequest(BaseModel):
    session_id: str = Field(..., min_length=8)


@router.post("/analyze")
async def analyze_documents(payload: AnalyzeRequest) -> JSONResponse:
    try:
        kernel = KernelService()
        results: Dict[str, Any] = await kernel.analyze_session(payload.session_id)
        return JSONResponse({"session_id": payload.session_id, "results": results})
    except Exception as e:
        logger.exception("Analyze error")
        raise HTTPException(status_code=500, detail=str(e))
