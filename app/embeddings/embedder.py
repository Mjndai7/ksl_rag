from sentence_transformers import SentenceTransformer
from typing import List


MODEL_NAME = "BAAI/bge-small-en-v1.5"

model = SentenceTransformer(MODEL_NAME)


def embed_text(text: str):
    return model.encode(
        text,
        normalize_embeddings=True,
    ).tolist()


def embed_chunks(chunks: List[str]):
    vectors = model.encode(
        chunks,
        normalize_embeddings=True,
    )

    return [v.tolist() for v in vectors]