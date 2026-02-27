from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import aiofiles
import structlog
from fastapi import FastAPI

from indexing_service.domain.models import IndexedChunk
from indexing_service.domain.services import ChunkingService, TextExtractionService
from indexing_service.infrastructure.consumer import RedpandaConsumer
from indexing_service.infrastructure.embedding_client import EmbeddingClient
from indexing_service.infrastructure.producer import RedpandaIndexingProducer
from indexing_service.infrastructure.repository import PostgresChunkRepository
from indexing_service.settings import Settings
from shared.logging.config import configure_logging
from shared.schemas.base import HealthResponse

settings = Settings()
configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger(__name__)

chunker = ChunkingService(
    chunk_size_tokens=settings.chunk_size_tokens,
    overlap_tokens=settings.chunk_overlap_tokens,
)
extractor = TextExtractionService()
embedding_client = EmbeddingClient(
    endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key.get_secret_value(),
    api_version=settings.azure_openai_api_version,
    deployment=settings.azure_openai_embedding_deployment,
)

_repository: PostgresChunkRepository | None = None
_producer: RedpandaIndexingProducer | None = None


async def handle_document_uploaded(payload: dict[str, Any]) -> None:
    global _repository, _producer

    event_id = str(payload.get("event_id", ""))
    document_id = UUID(payload["document_id"])
    tenant_id = payload["tenant_id"]
    storage_path = payload["storage_path"]
    content_type = payload["content_type"]
    correlation_id = UUID(str(payload.get("correlation_id", "")))

    log = logger.bind(
        document_id=str(document_id),
        tenant_id=tenant_id,
        correlation_id=str(correlation_id),
    )

    if _repository and await _repository.is_event_processed(event_id, settings.consumer_group_id):
        log.debug("indexing.event.already_processed", event_id=event_id)
        return

    log.info("indexing.document.started")

    if _repository:
        await _repository.update_document_status(document_id, "indexing")

    async with aiofiles.open(storage_path, "rb") as f:
        content = await f.read()

    text, page_count = extractor.extract(content, content_type)
    raw_chunks = chunker.chunk_text(document_id, tenant_id, text)

    if not raw_chunks:
        log.warning("indexing.document.no_chunks_extracted")
        if _repository:
            await _repository.update_document_status(document_id, "failed")
        return

    texts = [c.content for c in raw_chunks]
    embeddings = await embedding_client.embed_texts(texts)

    indexed_chunks = [
        IndexedChunk(
            chunk_id=raw.chunk_id,
            document_id=raw.document_id,
            tenant_id=raw.tenant_id,
            content=raw.content,
            page_number=raw.page_number,
            chunk_index=raw.chunk_index,
            token_count=raw.token_count,
            embedding=embeddings[i],
            embedding_model=settings.azure_openai_embedding_deployment,
        )
        for i, raw in enumerate(raw_chunks)
    ]

    if _repository:
        await _repository.save_chunks_batch(indexed_chunks)
        await _repository.update_document_status(
            document_id, "indexed",
            chunk_count=len(indexed_chunks),
            page_count=page_count,
        )
        await _repository.mark_event_processed(event_id, settings.consumer_group_id)

    if _producer:
        await _producer.publish_document_indexed(
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            document_id=document_id,
            chunk_count=len(indexed_chunks),
            page_count=page_count,
            embedding_model=settings.azure_openai_embedding_deployment,
        )

    log.info("indexing.document.completed", chunk_count=len(indexed_chunks), page_count=page_count)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _repository, _producer

    logger.info("service.starting", version=settings.app_version)

    _repository = PostgresChunkRepository(database_url=settings.database_url.get_secret_value())
    _producer = RedpandaIndexingProducer(bootstrap_servers=settings.redpanda_bootstrap_servers)
    await _producer.start()

    consumer = RedpandaConsumer(
        bootstrap_servers=settings.redpanda_bootstrap_servers,
        topic=settings.consumer_topic,
        group_id=settings.consumer_group_id,
        handler=handle_document_uploaded,
    )
    await consumer.start()
    consume_task = asyncio.create_task(consumer.consume())
    app.state.consumer = consumer

    logger.info("service.ready", topic=settings.consumer_topic)
    yield

    consume_task.cancel()
    await consumer.stop()
    await _producer.stop()
    await _repository.dispose()
    logger.info("service.stopped")


app = FastAPI(
    title="Indexing Service",
    description="Consumes document.uploaded events, chunks documents, generates embeddings, stores in pgvector.",
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
