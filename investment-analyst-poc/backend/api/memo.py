from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ..services.semantic_kernel_service import KernelService
from ..utils.logger import get_logger

router = APIRouter(prefix="/memo", tags=["memo"]) 
logger = get_logger(__name__)


class MemoRequest(BaseModel):
    session_id: str = Field(...)


@router.post("/generate")
async def generate_memo(payload: MemoRequest):
    try:
        kernel = KernelService()
        results = await kernel.analyze_session(payload.session_id)
        return JSONResponse({"memo": results.get("investment_memo", {})})
    except Exception as e:
        logger.exception("Memo generation error")
        raise HTTPException(status_code=500, detail=str(e))
