from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ingestion_service.domain.interfaces import DocumentRepositoryPort
from ingestion_service.domain.models import UploadedDocument

logger = structlog.get_logger(__name__)


class PostgresDocumentRepository(DocumentRepositoryPort):
    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url, pool_size=5, max_overflow=10
        )
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def save(self, document: UploadedDocument) -> None:
        sql = text("""
            INSERT INTO documents (
                id, tenant_id, filename, content_type,
                file_size_bytes, storage_path, status,
                uploaded_by, uploaded_at
            ) VALUES (
                :id, :tenant_id, :filename, :content_type,
                :file_size_bytes, :storage_path, :status,
                :uploaded_by, :uploaded_at
            )
            ON CONFLICT (id) DO NOTHING
        """)

        async with self._session_factory() as session:
            await session.execute(
                sql,
                {
                    "id": document.document_id,
                    "tenant_id": document.tenant_id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "file_size_bytes": document.file_size_bytes,
                    "storage_path": document.storage_path,
                    "status": document.status.value,
                    "uploaded_by": document.uploaded_by,
                    "uploaded_at": document.uploaded_at,
                },
            )
            await session.commit()

        logger.debug(
            "repository.document.saved",
            document_id=str(document.document_id),
            tenant_id=document.tenant_id,
        )

    async def get_by_id(self, document_id: UUID, tenant_id: str) -> UploadedDocument | None:
        sql = text("""
            SELECT id, tenant_id, filename, content_type,
                   file_size_bytes, storage_path, status,
                   uploaded_by, uploaded_at
            FROM documents
            WHERE id = :id AND tenant_id = :tenant_id
        """)

        async with self._session_factory() as session:
            result = await session.execute(sql, {"id": document_id, "tenant_id": tenant_id})
            row = result.mappings().first()

        if not row:
            return None

        return UploadedDocument(
            document_id=row["id"],
            tenant_id=row["tenant_id"],
            filename=row["filename"],
            content_type=row["content_type"],
            file_size_bytes=row["file_size_bytes"],
            storage_path=row["storage_path"],
            status=row["status"],
            uploaded_by=row["uploaded_by"],
            uploaded_at=row["uploaded_at"],
        )

    async def dispose(self) -> None:
        await self._engine.dispose()
