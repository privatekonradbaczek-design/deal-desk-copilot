from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = structlog.get_logger(__name__)

MessageHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class RedpandaConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        handler: MessageHandler,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._handler = handler
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "consumer.started",
            topic=self._topic,
            group_id=self._group_id,
        )

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("consumer.stopped")

    async def consume(self) -> None:
        if not self._consumer:
            raise RuntimeError("Consumer not started.")

        async for message in self._consumer:
            if not self._running:
                break
            try:
                await self._handler(message.value)
                await self._consumer.commit()
            except Exception as exc:
                logger.error(
                    "consumer.message.processing_failed",
                    topic=message.topic,
                    offset=message.offset,
                    error=str(exc),
                    exc_info=True,
                )
                # Do not commit — message will be redelivered
