from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from indexing_service.domain.models import IndexedChunk

logger = structlog.get_logger(__name__)


class PostgresChunkRepository:
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url, pool_size=5, max_overflow=10
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def save_chunks_batch(self, chunks: list[IndexedChunk]) -> None:
        if not chunks:
            return

        insert_sql = text("""
            INSERT INTO document_chunks (
                id, document_id, tenant_id, content,
                page_number, chunk_index, token_count,
                embedding_model, embedding
            ) VALUES (
                :id, :document_id, :tenant_id, :content,
                :page_number, :chunk_index, :token_count,
                :embedding_model, :embedding::vector
            )
            ON CONFLICT (id) DO NOTHING
        """)

        rows = [
            {
                "id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "tenant_id": chunk.tenant_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "embedding_model": chunk.embedding_model,
                "embedding": "[" + ",".join(str(v) for v in chunk.embedding) + "]",
            }
            for chunk in chunks
        ]

        async with self._session_factory() as session:
            await session.execute(insert_sql, rows)
            await session.commit()

        logger.info(
            "repository.chunks.saved",
            document_id=str(chunks[0].document_id),
            chunk_count=len(chunks),
        )

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        chunk_count: int | None = None,
        page_count: int | None = None,
    ) -> None:
        sql = text("""
            UPDATE documents
            SET status = :status,
                chunk_count = COALESCE(:chunk_count, chunk_count),
                page_count  = COALESCE(:page_count, page_count),
                updated_at  = NOW()
            WHERE id = :id
        """)

        async with self._session_factory() as session:
            await session.execute(
                sql,
                {
                    "id": document_id,
                    "status": status,
                    "chunk_count": chunk_count,
                    "page_count": page_count,
                },
            )
            await session.commit()

    async def is_event_processed(self, event_id: str, consumer_group: str) -> bool:
        sql = text("""
            SELECT 1 FROM processed_events
            WHERE event_id = :event_id AND consumer_group = :consumer_group
        """)
        async with self._session_factory() as session:
            result = await session.execute(
                sql, {"event_id": event_id, "consumer_group": consumer_group}
            )
            return result.first() is not None

    async def mark_event_processed(self, event_id: str, consumer_group: str) -> None:
        sql = text("""
            INSERT INTO processed_events (event_id, consumer_group)
            VALUES (:event_id, :consumer_group)
            ON CONFLICT DO NOTHING
        """)
        async with self._session_factory() as session:
            await session.execute(
                sql, {"event_id": event_id, "consumer_group": consumer_group}
            )
            await session.commit()

    async def dispose(self) -> None:
        await self._engine.dispose()
