from __future__ import annotations

from uuid import UUID

from shared.events.base import BaseEvent


class DocumentUploadedEvent(BaseEvent):
    document_id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    storage_path: str
    uploaded_by: str

    @property
    def topic(self) -> str:
        return "document.uploaded"


class DocumentIndexedEvent(BaseEvent):
    document_id: UUID
    chunk_count: int
    embedding_model: str
    page_count: int

    @property
    def topic(self) -> str:
        return "document.indexed"


class DocumentIndexingFailedEvent(BaseEvent):
    document_id: UUID
    error_code: str
    error_message: str

    @property
    def topic(self) -> str:
        return "document.indexing_failed"
