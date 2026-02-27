from __future__ import annotations

import json

import structlog
from aiokafka import AIOKafkaProducer

from ingestion_service.domain.interfaces import EventPublisherPort
from ingestion_service.domain.models import UploadedDocument
from shared.events.document_events import DocumentUploadedEvent

logger = structlog.get_logger(__name__)


class RedpandaEventPublisher(EventPublisherPort):
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
        )
        await self._producer.start()
        logger.info("producer.started", bootstrap_servers=self._bootstrap_servers)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("producer.stopped")

    async def publish_document_uploaded(
        self, document: UploadedDocument, correlation_id: str
    ) -> None:
        if not self._producer:
            raise RuntimeError("Producer is not started. Call start() first.")

        from uuid import UUID

        event = DocumentUploadedEvent(
            correlation_id=UUID(correlation_id),
            tenant_id=document.tenant_id,
            document_id=document.document_id,
            filename=document.filename,
            content_type=document.content_type,
            file_size_bytes=document.file_size_bytes,
            storage_path=document.storage_path,
            uploaded_by=document.uploaded_by,
        )

        await self._producer.send_and_wait(
            topic=event.topic,
            value=event.model_dump(mode="json"),
            key=document.tenant_id,
        )

        logger.info(
            "event.published",
            topic=event.topic,
            event_id=str(event.event_id),
            document_id=str(document.document_id),
        )
