from __future__ import annotations

import structlog
from openai import AsyncAzureOpenAI

logger = structlog.get_logger(__name__)


class EmbeddingClient:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        api_version: str,
        deployment: str,
    ) -> None:
        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._deployment = deployment

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            input=texts,
            model=self._deployment,
        )

        embeddings = [item.embedding for item in response.data]

        logger.debug(
            "embedding.batch.completed",
            count=len(texts),
            model=self._deployment,
            total_tokens=response.usage.total_tokens,
        )
        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0]
