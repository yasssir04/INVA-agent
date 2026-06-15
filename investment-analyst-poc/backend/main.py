from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .config import settings
from .utils.logger import get_logger
from .api.documents import router as documents_router
from .api.analysis import router as analysis_router
from .api.opportunities import router as opportunities_router
from .api.reports import router as reports_router
from .api.memo import router as memo_router
from .api.sessions import router as sessions_router

logger = get_logger(__name__, settings.log_level)

app = FastAPI(title="AI Investment Analyst POC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

app.include_router(documents_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(memo_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
