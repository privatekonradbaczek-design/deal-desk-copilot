from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import Field

from shared.events.base import BaseEvent


class DocumentUploadedEvent(BaseEvent):
    """Emitted by ingestion_service after a document is validated and persisted to storage.

    Consumed by: indexing_service (consumer group: indexing-service-group)
    Topic: document.uploaded
    Partition key: tenant_id

    Example payload:
    {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "document.uploaded",
        "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "tenant_id": "tenant_acme",
        "schema_version": "1.0",
        "timestamp_utc": "2026-02-27T15:00:00.000Z",
        "uploaded_at": "2026-02-27T15:00:00.000Z",
        "document_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
        "filename": "service_agreement_2024.pdf",
        "content_type": "application/pdf",
        "file_size_bytes": 204800,
        "storage_path": "/app/storage/a3bb189e/service_agreement_2024.pdf",
        "uploaded_by": "user_konrad"
    }
    """

    event_type: Literal["document.uploaded"] = Field(
        default="document.uploaded",
        description="Discriminator field — always 'document.uploaded'.",
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the document was accepted by ingestion_service.",
    )
    document_id: UUID = Field(description="Unique identifier of the persisted document.")
    filename: str = Field(description="Original filename as provided by the uploader.")
    content_type: str = Field(description="MIME type of the document binary.")
    file_size_bytes: int = Field(ge=1, description="File size in bytes.")
    storage_path: str = Field(description="Absolute path to the document on the storage volume.")
    uploaded_by: str = Field(description="Identifier of the user who initiated the upload.")

    @property
    def topic(self) -> str:
        return "document.uploaded"


class DocumentIndexedEvent(BaseEvent):
    """Emitted by indexing_service after all chunks and embeddings are persisted to pgvector.

    Consumed by: audit_service, downstream notification handlers.
    Topic: document.indexed
    Partition key: tenant_id

    Example payload:
    {
        "event_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "event_type": "document.indexed",
        "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "tenant_id": "tenant_acme",
        "schema_version": "1.0",
        "timestamp_utc": "2026-02-27T15:01:42.000Z",
        "indexed_at": "2026-02-27T15:01:42.000Z",
        "document_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
        "chunk_count": 47,
        "page_count": 12,
        "embedding_model": "text-embedding-ada-002"
    }
    """

    event_type: Literal["document.indexed"] = Field(
        default="document.indexed",
        description="Discriminator field — always 'document.indexed'.",
    )
    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when indexing pipeline completed successfully.",
    )
    document_id: UUID = Field(description="Unique identifier of the indexed document.")
    chunk_count: int = Field(ge=1, description="Total number of chunks stored in pgvector.")
    page_count: int = Field(ge=1, description="Total number of pages extracted from the document.")
    embedding_model: str = Field(description="Identifier of the Azure OpenAI embedding deployment used.")

    @property
    def topic(self) -> str:
        return "document.indexed"


class DocumentIndexingFailedEvent(BaseEvent):
    """Emitted by indexing_service when the indexing pipeline fails unrecoverably.

    Consumed by: audit_service, alerting handlers.
    Topic: document.indexing_failed
    Partition key: tenant_id

    Example payload:
    {
        "event_id": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "event_type": "document.indexing_failed",
        "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "tenant_id": "tenant_acme",
        "schema_version": "1.0",
        "timestamp_utc": "2026-02-27T15:01:55.000Z",
        "document_id": "a3bb189e-8bf9-3888-9912-ace4e6543002",
        "error_code": "EMBEDDING_API_UNAVAILABLE",
        "error_message": "Azure OpenAI returned 503 after 5 retry attempts."
    }
    """

    event_type: Literal["document.indexing_failed"] = Field(
        default="document.indexing_failed",
        description="Discriminator field — always 'document.indexing_failed'.",
    )
    document_id: UUID = Field(description="Unique identifier of the document that failed indexing.")
    error_code: str = Field(description="Machine-readable error code for programmatic handling.")
    error_message: str = Field(description="Human-readable description of the failure cause.")

    @property
    def topic(self) -> str:
        return "document.indexing_failed"
