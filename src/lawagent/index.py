"""Create and inspect the Qdrant collection used by LawAgent."""

from qdrant_client import QdrantClient, models

from lawagent.config import (
    EMBEDDING_DIMENSIONS,
    QDRANT_COLLECTION,
    QDRANT_URL,
)


PAYLOAD_INDEXES = {
    "status": models.PayloadSchemaType.KEYWORD,
    "doc_id": models.PayloadSchemaType.KEYWORD,
    "hierarchy_level": models.PayloadSchemaType.INTEGER,
    "effective_from": models.PayloadSchemaType.DATETIME,
    "effective_to": models.PayloadSchemaType.DATETIME,
}


def create_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"Created collection: {QDRANT_COLLECTION}")
    else:
        print(f"Collection already exists: {QDRANT_COLLECTION}")

    collection = client.get_collection(QDRANT_COLLECTION)
    existing_indexes = collection.payload_schema

    for field_name, field_schema in PAYLOAD_INDEXES.items():
        if field_name in existing_indexes:
            print(f"Payload index already exists: {field_name}")
            continue

        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name=field_name,
            field_schema=field_schema,
        )
        print(f"Created payload index: {field_name}")


def main() -> None:
    client = create_client()
    ensure_collection(client)

    collection = client.get_collection(QDRANT_COLLECTION)
    print(f"Status: {collection.status}")
    print(f"Points: {collection.points_count}")
    print(f"Payload indexes: {sorted(collection.payload_schema)}")


if __name__ == "__main__":
    main()