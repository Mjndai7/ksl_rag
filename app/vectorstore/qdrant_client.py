from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


client = QdrantClient(
    url="http://localhost:6333"
)

COLLECTION_NAME = "documents"


def init_qdrant(
    dimension=384,
):

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