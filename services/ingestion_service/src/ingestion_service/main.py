from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ingestion_service.api.routes import router
from ingestion_service.infrastructure.producer import RedpandaEventPublisher
from ingestion_service.infrastructure.repository import PostgresDocumentRepository
from ingestion_service.infrastructure.storage import LocalFileStorage
from ingestion_service.settings import Settings
from shared.logging.config import configure_logging

settings = Settings()
configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "service.starting",
        version=settings.app_version,
        environment=settings.environment,
        bootstrap_servers=settings.redpanda_bootstrap_servers,
    )

    storage = LocalFileStorage(base_path=settings.storage_base_path)
    repository = PostgresDocumentRepository(
        database_url=settings.database_url.get_secret_value()
    )
    publisher = RedpandaEventPublisher(
        bootstrap_servers=settings.redpanda_bootstrap_servers
    )

    try:
        await publisher.start()
    except Exception as exc:
        logger.critical(
            "service.startup.failed",
            component="kafka_producer",
            error=str(exc),
        )
        raise

    app.state.storage = storage
    app.state.repository = repository
    app.state.publisher = publisher

    logger.info("service.ready", port=settings.service_port)
    yield

    await publisher.stop()
    await repository.dispose()
    logger.info("service.stopped")


app = FastAPI(
    title="Ingestion Service",
    description="Accepts document uploads, validates, stores, and emits docs.uploaded events.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(router)
