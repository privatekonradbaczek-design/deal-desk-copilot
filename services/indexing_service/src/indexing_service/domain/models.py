from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    tenant_id: str
    content: str
    page_number: int | None
    chunk_index: int
    token_count: int


class IndexedChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    document_id: UUID
    tenant_id: str
    content: str
    page_number: int | None
    chunk_index: int
    token_count: int
    embedding: list[float]
    embedding_model: str
