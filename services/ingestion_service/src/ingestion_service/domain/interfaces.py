from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ingestion_service.domain.models import UploadedDocument


class DocumentStoragePort(ABC):
    @abstractmethod
    async def save(self, document_id: UUID, filename: str, content: bytes) -> str:
        """Persist document binary. Returns storage_path."""

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check whether a document exists at the given path."""


class DocumentRepositoryPort(ABC):
    @abstractmethod
    async def save(self, document: UploadedDocument) -> None:
        """Persist document metadata record."""

    @abstractmethod
    async def get_by_id(self, document_id: UUID, tenant_id: str) -> UploadedDocument | None:
        """Retrieve document metadata by ID scoped to tenant."""


class EventPublisherPort(ABC):
    @abstractmethod
    async def publish_document_uploaded(self, document: UploadedDocument, correlation_id: str) -> None:
        """Emit document.uploaded event to event bus."""
