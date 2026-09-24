"""Embed legal chunks and ingest them into Qdrant."""

import json
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from openai import OpenAI
from qdrant_client import QdrantClient, models

from lawagent.config import (
    EMBEDDING_DIMENSIONS,
    OPENAI_EMBEDDING_MODEL,
    QDRANT_COLLECTION,
    QDRANT_URL,
)
from lawagent.index import ensure_collection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
BATCH_SIZE = 32


def load_chunks() -> list[dict]:
    chunks: list[dict] = []

    with CHUNKS_PATH.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            chunk = json.loads(line)

            if not chunk.get("chunk_id"):
                raise ValueError(f"Missing chunk_id at line {line_number}")

            if not chunk.get("text_for_embedding"):
                raise ValueError(
                    f"Missing text_for_embedding for {chunk['chunk_id']}"
                )

            chunks.append(chunk)

    return chunks


def point_id(chunk_id: str) -> str:
    """Qdrant IDs must be integers or UUIDs."""
    return str(uuid5(NAMESPACE_URL, f"lawagent:{chunk_id}"))


def to_qdrant_datetime(value: str | None) -> str | None:
    """Convert YYYY-MM-DD into an RFC 3339 datetime."""
    if value is None:
        return None

    parsed = date.fromisoformat(value)
    return f"{parsed.isoformat()}T00:00:00Z"


def build_payload(chunk: dict) -> dict:
    payload = dict(chunk)
    payload["effective_from"] = to_qdrant_datetime(
        chunk["effective_from"]
    )
    payload["effective_to"] = to_qdrant_datetime(
        chunk.get("effective_to")
    )
    payload["embedding_model"] = OPENAI_EMBEDDING_MODEL
    payload["embedding_dimensions"] = EMBEDDING_DIMENSIONS
    return payload


def batched(items: list[dict], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def ingest() -> None:
    chunks = load_chunks()
    qdrant = QdrantClient(url=QDRANT_URL)
    openai = OpenAI()

    ensure_collection(qdrant)

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_number, batch in enumerate(
        batched(chunks, BATCH_SIZE),
        start=1,
    ):
        ids = [point_id(chunk["chunk_id"]) for chunk in batch]

        existing_points = qdrant.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=ids,
            with_payload=False,
            with_vectors=False,
        )
        existing_ids = {str(point.id) for point in existing_points}

        missing = [
            (chunk, identifier)
            for chunk, identifier in zip(batch, ids, strict=True)
            if identifier not in existing_ids
        ]

        if not missing:
            print(
                f"Batch {batch_number}/{total_batches}: "
                f"already ingested"
            )
            continue

        texts = [
            chunk["text_for_embedding"]
            for chunk, _ in missing
        ]

        response = openai.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=texts,
            dimensions=EMBEDDING_DIMENSIONS,
            encoding_format="float",
        )

        vectors: list[list[float] | None] = [None] * len(missing)
        for item in response.data:
            vectors[item.index] = item.embedding

        points = []
        for (chunk, identifier), vector in zip(
            missing,
            vectors,
            strict=True,
        ):
            if vector is None:
                raise RuntimeError(
                    f"Missing embedding for {chunk['chunk_id']}"
                )

            points.append(
                models.PointStruct(
                    id=identifier,
                    vector=vector,
                    payload=build_payload(chunk),
                )
            )

        qdrant.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points,
            wait=True,
        )

        print(
            f"Batch {batch_number}/{total_batches}: "
            f"ingested {len(points)} points; "
            f"tokens={response.usage.total_tokens}"
        )

    collection = qdrant.get_collection(QDRANT_COLLECTION)
    print(f"Completed. Qdrant points: {collection.points_count}")


def main() -> None:
    ingest()


if __name__ == "__main__":
    main()