"""Dense retrieval using OpenAI embeddings and Qdrant."""

from dataclasses import dataclass
from datetime import date

from openai import OpenAI
from qdrant_client import QdrantClient

from lawagent.config import (
    EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    QDRANT_COLLECTION,
    QDRANT_URL,
)
from lawagent.temporal_filter import build_temporal_filter


@dataclass(frozen=True)
class DenseResult:
    rank: int
    score: float
    chunk: dict


class DenseRetriever:
    def __init__(
        self,
        openai_client: OpenAI | None = None,
        qdrant_client: QdrantClient | None = None,
    ) -> None:
        self.openai = openai_client or OpenAI()
        self.qdrant = qdrant_client or QdrantClient(
            url=QDRANT_URL
        )

    def embed_query(self, query: str) -> list[float]:
        query = query.strip()

        if not query:
            raise ValueError("Query must not be empty")

        response = self.openai.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=[query],
            dimensions=EMBEDDING_DIMENSIONS,
            encoding_format="float",
        )

        vector = response.data[0].embedding

        if len(vector) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "Unexpected embedding dimensions: "
                f"expected {EMBEDDING_DIMENSIONS}, "
                f"received {len(vector)}"
            )

        return vector

    def search(
        self,
        query: str,
        as_of: date,
        limit: int = 10,
    ) -> list[DenseResult]:
        if limit < 1:
            raise ValueError("Limit must be positive")

        vector = self.embed_query(query)

        response = self.qdrant.query_points(
            collection_name=QDRANT_COLLECTION,
            query=vector,
            query_filter=build_temporal_filter(as_of),
            with_payload=True,
            with_vectors=False,
            limit=limit,
        )

        results: list[DenseResult] = []

        for rank, point in enumerate(
            response.points,
            start=1,
        ):
            payload = dict(point.payload or {})

            if not payload.get("chunk_id"):
                raise RuntimeError(
                    f"Qdrant point {point.id} has no chunk_id"
                )

            results.append(
                DenseResult(
                    rank=rank,
                    score=float(point.score),
                    chunk=payload,
                )
            )

        return results