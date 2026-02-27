from __future__ import annotations

from fastapi import Request

from ingestion_service.domain.interfaces import (
    DocumentRepositoryPort,
    DocumentStoragePort,
    EventPublisherPort,
)
from ingestion_service.domain.services import IngestionService
from ingestion_service.settings import Settings

_settings = Settings()


def get_storage(request: Request) -> DocumentStoragePort:
    return request.app.state.storage


def get_publisher(request: Request) -> EventPublisherPort:
    return request.app.state.publisher


def get_ingestion_service(request: Request) -> IngestionService:
    return IngestionService(
        storage=request.app.state.storage,
        repository=request.app.state.repository,
        publisher=request.app.state.publisher,
        max_file_size_bytes=_settings.max_document_size_mb * 1024 * 1024,
    )
