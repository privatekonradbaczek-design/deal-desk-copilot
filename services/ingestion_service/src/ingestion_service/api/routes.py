from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from ingestion_service.api.dependencies import get_ingestion_service
from ingestion_service.domain.exceptions import (
    DocumentTooLargeError,
    IngestionError,
    UnsupportedContentTypeError,
)
from ingestion_service.domain.models import DocumentUploadResponse
from ingestion_service.domain.services import IngestionService
from ingestion_service.settings import Settings
from shared.logging.config import bind_request_context
from shared.schemas.base import ErrorResponse, HealthResponse

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = Settings()


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.app_version,
    )


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=202,
    tags=["ingestion"],
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    uploaded_by: str = Form(...),
    service: IngestionService = Depends(get_ingestion_service),
) -> DocumentUploadResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    bind_request_context(correlation_id=correlation_id, tenant_id=tenant_id, user_id=uploaded_by)

    log = logger.bind(
        correlation_id=correlation_id,
        filename=file.filename,
        tenant_id=tenant_id,
    )
    log.info("ingestion.request.received")

    content = await file.read()

    try:
        document = await service.ingest_document(
            tenant_id=tenant_id,
            uploaded_by=uploaded_by,
            filename=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            content=content,
            correlation_id=correlation_id,
        )
    except UnsupportedContentTypeError as exc:
        raise HTTPException(status_code=415, detail=exc.error_code) from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=exc.error_code) from exc
    except IngestionError as exc:
        log.error("ingestion.request.failed", error_code=exc.error_code, error=str(exc))
        raise HTTPException(status_code=500, detail=exc.error_code) from exc

    return DocumentUploadResponse(
        document_id=document.document_id,
        filename=document.filename,
        status=document.status,
        correlation_id=correlation_id,
    )
