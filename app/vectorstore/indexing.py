import uuid
from typing import List

from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue, PointStruct

from app.chunking.splitter import Chunk
from app.vectorstore.qdrant_client import COLLECTION_NAME, get_qdrant_client

_POINT_NAMESPACE = uuid.UUID("5b0f3c1e-7a8b-4f0e-9a51-6a3c1f9d2e10")


def point_id(document_id: str, chunk_index: int) -> str:
    """Deterministic id so re-ingesting a document overwrites its points instead of duplicating."""
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{document_id}:{chunk_index}"))


def delete_document_points(document_id: str) -> None:
    get_qdrant_client().delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        ),
        wait=True,
    )


def upsert_chunks(
    chunks: List[Chunk],
    embeddings: List[list],
    metadata: dict,
    batch_size: int = 128,
) -> int:
    """Replace all points for metadata["document_id"] with the given chunks."""
    if len(chunks) != len(embeddings):
        raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")

    document_id = metadata["document_id"]
    delete_document_points(document_id)

    points = [
        PointStruct(
            id=point_id(document_id, chunk.index),
            vector=vector,
            payload={
                "text": chunk.text,
                "chunk_index": chunk.index,
                "sections": chunk.sections,
                "section_label": chunk.section_label,
                "headings": chunk.headings,
                **metadata,
            },
        )
        for chunk, vector in zip(chunks, embeddings)
    ]

    client = get_qdrant_client()
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=COLLECTION_NAME, points=points[i:i + batch_size], wait=True)
    return len(points)


def semantic_search(query_vector, limit=5):
    results = get_qdrant_client().query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return results.points
