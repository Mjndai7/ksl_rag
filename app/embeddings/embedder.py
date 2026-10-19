from typing import List
import logging

from app.core.openrouter import get_openrouter_client
from app.core.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


def _embed(inputs: List[str]) -> List[List[float]]:
    response = get_openrouter_client().embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=inputs,
    )
    data = sorted(response.data, key=lambda d: d.index)
    vectors = [d.embedding for d in data]

    if len(vectors) != len(inputs):
        raise EmbeddingError(f"Expected {len(inputs)} embeddings, got {len(vectors)}")
    for v in vectors:
        if len(v) != settings.EMBEDDING_DIM:
            raise EmbeddingError(
                f"Embedding model {settings.EMBEDDING_MODEL} returned {len(v)} dims, "
                f"but EMBEDDING_DIM={settings.EMBEDDING_DIM}"
            )
    return vectors


def embed_query(query: str) -> List[float]:
    """Embed a retrieval query."""
    return _embed([query])[0]


def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Batch embed text chunks. Raises instead of storing placeholder vectors on failure."""
    all_embeddings: List[List[float]] = []
    batch_size = settings.EMBEDDING_BATCH_SIZE

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            all_embeddings.extend(_embed(batch))
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Embedding batch {i // batch_size} failed: {e}") from e

    return all_embeddings
