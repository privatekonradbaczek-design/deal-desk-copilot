from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from retrieval_service.domain.models import RetrievalRequest, RetrievalResult
from shared.schemas.documents import RetrievedChunk

logger = structlog.get_logger(__name__)


class PgVectorRetrievalRepository:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url, pool_size=10, max_overflow=20
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def similarity_search(
        self,
        query_embedding: list[float],
        request: RetrievalRequest,
    ) -> RetrievalResult:
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        sql = text("""
            SELECT
                dc.id AS chunk_id,
                dc.document_id,
                dc.tenant_id,
                dc.content,
                dc.page_number,
                dc.chunk_index,
                d.filename AS document_filename,
                1 - (dc.embedding <=> :embedding::vector) AS similarity_score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.tenant_id = :tenant_id
              AND 1 - (dc.embedding <=> :embedding::vector) >= :threshold
            ORDER BY dc.embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        async with self._session_factory() as session:
            result = await session.execute(
                sql,
                {
                    "embedding": embedding_str,
                    "tenant_id": request.tenant_id,
                    "threshold": request.similarity_threshold,
                    "top_k": request.top_k,
                },
            )
            rows = result.mappings().all()

        chunks = [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                tenant_id=row["tenant_id"],
                content=row["content"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                similarity_score=float(row["similarity_score"]),
                document_filename=row["document_filename"],
            )
            for row in rows
        ]

        if not chunks:
            return RetrievalResult.empty(
                query=request.query,
                tenant_id=request.tenant_id,
                reason="NO_RELEVANT_CONTEXT",
            )

        logger.info(
            "retrieval.similarity_search.completed",
            tenant_id=request.tenant_id,
            chunk_count=len(chunks),
            top_score=chunks[0].similarity_score if chunks else 0.0,
        )

        return RetrievalResult(
            query=request.query,
            tenant_id=request.tenant_id,
            chunks=chunks,
            has_context=True,
        )

    async def dispose(self) -> None:
        await self._engine.dispose()
