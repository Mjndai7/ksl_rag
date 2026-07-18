from typing import List
import logging

from openai import OpenAI
from app.core.settings import settings

logger = logging.getLogger(__name__)

# Use Alibaba's text-embedding-v4 via OpenAI-compatible endpoint
embedding_client = OpenAI(
    api_key=settings.ALIBABA_API_KEY,
    base_url=settings.ALIBABA_API_BASE
)

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIMENSION = 1024


def embed_text(text: str) -> List[float]:
    """Embed a single document text."""
    response = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embed_query(query: str) -> List[float]:
    """Embed a retrieval query."""
    response = embedding_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    return response.data[0].embedding


def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Batch embed a list of text chunks."""
    all_embeddings = []
    batch_size = 10  # Alibaba API max batch size is 10

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            response = embedding_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])
        except Exception as e:
            logger.error(f"Embedding batch {i//batch_size} failed: {e}")
            # Fallback: embed one by one
            for chunk in batch:
                try:
                    emb = embed_text(chunk)
                    all_embeddings.append(emb)
                except Exception as ex:
                    logger.error(f"Single embedding failed: {ex}")
                    all_embeddings.append([0.0] * EMBEDDING_DIMENSION)

    return all_embeddings  