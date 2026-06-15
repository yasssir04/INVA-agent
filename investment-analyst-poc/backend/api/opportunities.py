from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger
from ..services.tavily_service import TavilyService

router = APIRouter(prefix="/opportunities", tags=["opportunities"]) 
logger = get_logger(__name__)


class OpportunityRequest(BaseModel):
    sector: str = Field(..., min_length=3)


@router.post("/search")
async def search_opportunities(payload: Optional[OpportunityRequest] = None, sector: Optional[str] = Query(None)) -> JSONResponse:
    try:
        chosen = (payload.sector if payload and payload.sector else sector or "").strip()
        if len(chosen) < 3:
            raise HTTPException(status_code=400, detail="Sector is required (min length 3)")
        svc = TavilyService()
        items: List[Dict[str, Any]] = await svc.search_qatar_opportunities(chosen)
        return JSONResponse({"opportunities": items})
    except Exception as e:
        logger.exception("Opportunity search error")
        raise HTTPException(status_code=500, detail=str(e))
