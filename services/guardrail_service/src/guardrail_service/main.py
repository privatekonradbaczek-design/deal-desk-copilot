from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from guardrail_service.domain.detector import InjectionDetector, PIIDetector
from guardrail_service.domain.models import (
    InputValidationRequest,
    InputValidationResponse,
    OutputValidationRequest,
    OutputValidationResponse,
)
from guardrail_service.settings import Settings
from shared.logging.config import bind_request_context, configure_logging
from shared.schemas.base import HealthResponse

settings = Settings()
configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger(__name__)

injection_detector = InjectionDetector(score_threshold=settings.injection_score_threshold)
pii_detector = PIIDetector()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("service.starting", version=settings.app_version)
    logger.info("service.ready", injection_threshold=settings.injection_score_threshold)
    yield
    logger.info("service.stopped")


app = FastAPI(
    title="Guardrail Service",
    description="Input/output validation: prompt injection detection, PII scanning, citation enforcement.",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.app_version,
    )


@app.post("/validate/input", response_model=InputValidationResponse, tags=["guardrail"])
async def validate_input(
    request: Request, body: InputValidationRequest
) -> InputValidationResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    bind_request_context(correlation_id=correlation_id, tenant_id=body.tenant_id)

    if len(body.text) > settings.max_query_length:
        logger.warning(
            "guardrail.input.rejected.length",
            text_length=len(body.text),
            limit=settings.max_query_length,
        )
        return InputValidationResponse(
            passed=False,
            injection_score=0.0,
            refusal_code="QUERY_TOO_LONG",
        )

    is_injection, score, patterns = injection_detector.is_injection(body.text)

    if is_injection:
        logger.warning(
            "guardrail.injection.detected",
            injection_score=score,
            matched_patterns=patterns,
            tenant_id=body.tenant_id,
        )
        return InputValidationResponse(
            passed=False,
            injection_score=score,
            refusal_code="INJECTION_DETECTED",
            matched_patterns=patterns,
        )

    logger.debug(
        "guardrail.input.passed",
        injection_score=score,
        tenant_id=body.tenant_id,
    )
    return InputValidationResponse(passed=True, injection_score=score)


@app.post("/validate/output", response_model=OutputValidationResponse, tags=["guardrail"])
async def validate_output(
    request: Request, body: OutputValidationRequest
) -> OutputValidationResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    bind_request_context(correlation_id=correlation_id, tenant_id=body.tenant_id)

    citation_count = len(body.citations)

    if not body.answer or not body.answer.strip():
        return OutputValidationResponse(
            passed=False,
            refusal_code="EMPTY_ANSWER",
            citation_count=citation_count,
        )

    if citation_count == 0:
        logger.warning("guardrail.output.no_citations", tenant_id=body.tenant_id)
        return OutputValidationResponse(
            passed=False,
            refusal_code="NO_CITATIONS",
            citation_count=0,
        )

    return OutputValidationResponse(passed=True, citation_count=citation_count)
