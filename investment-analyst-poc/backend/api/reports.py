from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from ..services.semantic_kernel_service import KernelService
from ..services.export_service import ExportService
from ..utils.logger import get_logger

router = APIRouter(prefix="/reports", tags=["reports"]) 
logger = get_logger(__name__)


class ExportQuery(BaseModel):
    session_id: str = Field(...)


@router.get("/export/{format}")
async def export_report(format: str, session_id: str) -> Response:
    if format not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Unsupported format")
    kernel = KernelService()
    results = await kernel.analyze_session(session_id)
    exporter = ExportService()
    if format == "pdf":
        data = exporter.export_pdf(results)
        return Response(
            data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=analysis_report.pdf"
            },
        )
    else:
        data = exporter.export_docx(results)
        return Response(
            data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": "attachment; filename=analysis_report.docx"
            },
        )
