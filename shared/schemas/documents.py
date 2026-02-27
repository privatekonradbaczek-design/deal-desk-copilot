from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    filename: str
    content_type: str
    file_size_bytes: int
    status: DocumentStatus
    tenant_id: str
    uploaded_by: str
    uploaded_at: datetime
    page_count: int | None = None
    chunk_count: int | None = None


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    tenant_id: str
    content: str
    page_number: int | None
    chunk_index: int
    token_count: int
    embedding_model: str


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    tenant_id: str
    content: str
    page_number: int | None
    chunk_index: int
    similarity_score: float = Field(ge=0.0, le=1.0)
    document_filename: str


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    document_filename: str
    page_number: int | None
    excerpt: str = Field(max_length=500)
    similarity_score: float = Field(ge=0.0, le=1.0)
