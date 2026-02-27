from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import aiofiles
import structlog

from ingestion_service.domain.exceptions import StorageError
from ingestion_service.domain.interfaces import DocumentStoragePort

logger = structlog.get_logger(__name__)


class LocalFileStorage(DocumentStoragePort):
    """Filesystem-based document storage.

    In production: replace with Azure Blob Storage adapter implementing the same interface.
    """

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, document_id: UUID, filename: str, content: bytes) -> str:
        doc_dir = self._base_path / str(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        file_path = doc_dir / filename

        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
        except OSError as exc:
            logger.error(
                "storage.write.failed",
                document_id=str(document_id),
                path=str(file_path),
                error=str(exc),
            )
            raise StorageError(str(exc)) from exc

        storage_path = str(file_path)
        logger.debug(
            "storage.write.success",
            document_id=str(document_id),
            path=storage_path,
            size_bytes=len(content),
        )
        return storage_path

    async def exists(self, storage_path: str) -> bool:
        return os.path.isfile(storage_path)
