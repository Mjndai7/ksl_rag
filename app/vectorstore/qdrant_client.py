from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from app.core.settings import settings


_client: Optional[QdrantClient] = None

COLLECTION_NAME = settings.QDRANT_COLLECTION


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            timeout=120,
            check_compatibility=False,
        )
    return _client


def init_qdrant(dimension: Optional[int] = None):
    """Create the collection if missing; fail loudly if it exists with a different vector size."""
    dimension = dimension or settings.EMBEDDING_DIM
    client = get_qdrant_client()

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
    else:
        info = client.get_collection(COLLECTION_NAME)
        existing = info.config.params.vectors.size
        if existing != dimension:
            raise RuntimeError(
                f"Qdrant collection '{COLLECTION_NAME}' has vector size {existing}, but "
                f"EMBEDDING_DIM={dimension} ({settings.EMBEDDING_MODEL}). Use a new "
                f"QDRANT_COLLECTION or delete the old collection and re-ingest."
            )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="document_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )
