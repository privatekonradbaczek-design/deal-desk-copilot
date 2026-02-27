from __future__ import annotations

import json
from uuid import UUID

import structlog
from aiokafka import AIOKafkaProducer

from shared.events.document_events import DocumentIndexedEvent

logger = structlog.get_logger(__name__)


class RedpandaIndexingProducer:
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

    async def publish_document_indexed(
        self,
        correlation_id: UUID,
        tenant_id: str,
        document_id: UUID,
        chunk_count: int,
        page_count: int,
        embedding_model: str,
    ) -> None:
        if not self._producer:
            raise RuntimeError("Producer is not started.")

        event = DocumentIndexedEvent(
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            document_id=document_id,
            chunk_count=chunk_count,
            page_count=page_count,
            embedding_model=embedding_model,
        )

        await self._producer.send_and_wait(
            topic=event.topic,
            value=event.model_dump(mode="json"),
            key=tenant_id,
        )

        logger.info(
            "event.published",
            topic=event.topic,
            event_id=str(event.event_id),
            document_id=str(document_id),
            chunk_count=chunk_count,
        )
