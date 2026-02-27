from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from openai import AsyncAzureOpenAI

from agent_service.api.routes import router
from agent_service.graph.builder import build_graph
from agent_service.settings import Settings
from shared.logging.config import configure_logging
from shared.schemas.base import HealthResponse

settings = Settings()
configure_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("service.starting", version=settings.app_version)

    openai_client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.azure_openai_api_version,
    )
    graph = build_graph(settings=settings, openai_client=openai_client)

    app.state.graph = graph
    app.state.openai_client = openai_client

    logger.info("service.ready", graph_nodes=list(graph.nodes.keys()))
    yield

    await openai_client.close()
    logger.info("service.stopped")


app = FastAPI(
    title="Agent Service",
    description="LangGraph-based agent orchestrator with explicit state machine for Q&A over contracts.",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.app_version,
    )


app.include_router(router)
