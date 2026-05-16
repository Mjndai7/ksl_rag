from typing import List

import torch
from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-small-en-v1.5"
device = "cuda" if torch.cuda.is_available() else "cpu"

model = SentenceTransformer(MODEL_NAME, device=device)

# single document embedding
def embed_text(text: str):
    text = f"passage: {text} " 
    return model.encode(
        text,
        normalize_embeddings=True,
    ).tolist()

# retrieveal query embedding
def embed_query(query: str):
    query = f"query: {query}"
    return model.encode(
        query,
        normalize_embeddings=True,
    ).tolist()

# batch embedding for chunks
def embed_chunks(chunks: List[str]):
    chunks = [f"passage: {c}" for c in chunks]
    vectors = model.encode(
        chunks,
        batch_size=32,
        normalize_embeddings=True,
    )

    return [v.tolist() for v in vectors]  