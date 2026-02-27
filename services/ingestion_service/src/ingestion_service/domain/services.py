from __future__ import annotations

import structlog

from ingestion_service.domain.exceptions import (
    DocumentTooLargeError,
    UnsupportedContentTypeError,
)
from ingestion_service.domain.interfaces import (
    DocumentRepositoryPort,
    DocumentStoragePort,
    EventPublisherPort,
)
from ingestion_service.domain.models import UploadedDocument

logger = structlog.get_logger(__name__)

ALLOWED_CONTENT_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
})
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class IngestionService:
    def __init__(
        self,
        storage: DocumentStoragePort,
        repository: DocumentRepositoryPort,
        publisher: EventPublisherPort,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        allowed_content_types: frozenset[str] = ALLOWED_CONTENT_TYPES,
    ) -> None:
        self._storage = storage
        self._repository = repository
        self._publisher = publisher
        self._max_file_size_bytes = max_file_size_bytes
        self._allowed_content_types = allowed_content_types

    async def ingest_document(
        self,
        tenant_id: str,
        uploaded_by: str,
        filename: str,
        content_type: str,
        content: bytes,
        correlation_id: str,
    ) -> UploadedDocument:
        log = logger.bind(
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            correlation_id=correlation_id,
        )

        if content_type not in self._allowed_content_types:
            log.warning("ingestion.rejected.unsupported_type", content_type=content_type)
            raise UnsupportedContentTypeError(content_type)

        if len(content) > self._max_file_size_bytes:
            log.warning(
                "ingestion.rejected.file_too_large",
                size_bytes=len(content),
                limit_bytes=self._max_file_size_bytes,
            )
            raise DocumentTooLargeError(len(content), self._max_file_size_bytes)

        document = UploadedDocument(
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            file_size_bytes=len(content),
            storage_path="",  # Populated after storage.save()
            uploaded_by=uploaded_by,
        )

        storage_path = await self._storage.save(
            document_id=document.document_id,
            filename=filename,
            content=content,
        )

        document = document.model_copy(update={"storage_path": storage_path})

        await self._repository.save(document)
        await self._publisher.publish_document_uploaded(document, correlation_id)

        log.info(
            "ingestion.document.accepted",
            document_id=str(document.document_id),
            file_size_bytes=document.file_size_bytes,
            storage_path=storage_path,
        )

        return document
