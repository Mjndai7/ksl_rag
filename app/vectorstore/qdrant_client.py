from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.settings import settings


_client: Optional[QdrantClient] = None

COLLECTION_NAME = settings.QDRANT_COLLECTION


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            timeout=60,
            check_compatibility=False,
        )
    return _client


def init_qdrant(dimension: int = 384):
    client = get_qdrant_client()

    existing = [
        c.name
        for c in client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE,
            ),
        )