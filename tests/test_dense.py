from datetime import date
from types import SimpleNamespace

import pytest

from lawagent.config import (
    EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    QDRANT_COLLECTION,
)
from lawagent.dense import DenseRetriever


class FakeEmbeddings:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1] * EMBEDDING_DIMENSIONS
                )
            ]
        )


class FakeOpenAI:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddings()


class FakeQdrant:
    def __init__(self) -> None:
        self.kwargs = None

    def query_points(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="point-1",
                    score=0.91,
                    payload={
                        "chunk_id": "doc__dieu_25",
                        "breadcrumb": "Điều 25",
                        "effective_from": (
                            "2026-07-01T00:00:00Z"
                        ),
                        "effective_to": None,
                    },
                )
            ]
        )


def test_dense_search_uses_embedding_and_filter() -> None:
    openai = FakeOpenAI()
    qdrant = FakeQdrant()
    retriever = DenseRetriever(openai, qdrant)

    results = retriever.search(
        "thời gian thử việc",
        as_of=date(2026, 9, 22),
        limit=5,
    )

    assert openai.embeddings.kwargs == {
        "model": OPENAI_EMBEDDING_MODEL,
        "input": ["thời gian thử việc"],
        "dimensions": EMBEDDING_DIMENSIONS,
        "encoding_format": "float",
    }

    assert qdrant.kwargs["collection_name"] == (
        QDRANT_COLLECTION
    )
    assert qdrant.kwargs["limit"] == 5
    assert qdrant.kwargs["query_filter"] is not None

    assert len(results) == 1
    assert results[0].rank == 1
    assert results[0].score == 0.91
    assert results[0].chunk["chunk_id"] == (
        "doc__dieu_25"
    )


def test_dense_search_rejects_empty_query() -> None:
    retriever = DenseRetriever(FakeOpenAI(), FakeQdrant())

    with pytest.raises(
        ValueError,
        match="Query must not be empty",
    ):
        retriever.search(
            "   ",
            as_of=date(2026, 9, 22),
        )