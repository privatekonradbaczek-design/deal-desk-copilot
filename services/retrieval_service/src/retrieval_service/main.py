from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from openai import AsyncAzureOpenAI

from retrieval_service.domain.models import RetrievalRequest, RetrievalResult
from retrieval_service.infrastructure.pgvector_repo import PgVectorRetrievalRepository
from retrieval_service.settings import Settings
from shared.logging.config import bind_request_context, configure_logging
from shared.schemas.base import HealthResponse

settings = Settings()
configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("service.starting", version=settings.app_version)

    openai_client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
    )
    repository = PgVectorRetrievalRepository(
        database_url=settings.database_url.get_secret_value()
    )

    app.state.openai_client = openai_client
    app.state.repository = repository
    app.state.settings = settings

    logger.info("service.ready")
    yield

    await repository.dispose()
    logger.info("service.stopped")


app = FastAPI(
    title="Retrieval Service",
    description="Performs semantic similarity search over pgvector embeddings.",
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


@app.post("/retrieve", response_model=RetrievalResult, tags=["retrieval"])
async def retrieve(request: Request, body: RetrievalRequest) -> RetrievalResult:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    bind_request_context(
        correlation_id=correlation_id,
        tenant_id=body.tenant_id,
    )

    log = logger.bind(correlation_id=correlation_id, tenant_id=body.tenant_id)
    log.info("retrieval.request.received", query_length=len(body.query))

    openai_client: AsyncAzureOpenAI = request.app.state.openai_client
    repository: PgVectorRetrievalRepository = request.app.state.repository

    embedding_response = await openai_client.embeddings.create(
        input=body.query,
        model=settings.azure_openai_embedding_deployment,
    )
    query_embedding = embedding_response.data[0].embedding

    result = await repository.similarity_search(
        query_embedding=query_embedding,
        request=body,
    )

    log.info(
        "retrieval.request.completed",
        has_context=result.has_context,
        chunk_count=len(result.chunks),
    )
    return result
