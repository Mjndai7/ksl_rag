import uuid
from typing import List

from qdrant_client.models import PointStruct

from app.vectorstore.qdrant_client import (
    COLLECTION_NAME,
    get_qdrant_client,
)


def upsert_chunks(
    chunks: List[str],
    embeddings: List[list],
    metadata: dict,
):

    points = []

    for chunk, vector in zip(
        chunks,
        embeddings,
    ):

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk,
                    **metadata,
                },
            )
        )

    client = get_qdrant_client()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )


def semantic_search(
    query_vector,
    limit=5,
):
    client = get_qdrant_client()

    if hasattr(client, "search"):
        return client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
    )
    return results.points