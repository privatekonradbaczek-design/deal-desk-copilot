from __future__ import annotations

from abc import ABC, abstractmethod

from retrieval_service.domain.models import RetrievalRequest, RetrievalResult


class RetrievalRepositoryPort(ABC):
    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        request: RetrievalRequest,
    ) -> RetrievalResult: ...
