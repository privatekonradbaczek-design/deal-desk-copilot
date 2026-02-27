from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.documents import DocumentStatus


class UploadedDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    filename: str
    content_type: str
    file_size_bytes: int
    storage_path: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: DocumentStatus = DocumentStatus.UPLOADED


class DocumentUploadRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(min_length=1, max_length=255)
    uploaded_by: str = Field(min_length=1, max_length=255)


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    filename: str
    status: DocumentStatus
    correlation_id: str
