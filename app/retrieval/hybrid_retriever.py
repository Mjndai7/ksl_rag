from app.embeddings.embedder import embed_query
from app.vectorstore.indexing import semantic_search


def retrieve(query: str):

    vector = embed_query(query)

    hits = semantic_search(
        query_vector=vector,
        limit=5,
    )

    contexts = []

    for hit in hits:
        contexts.append(
            hit.payload["text"]
        )

    return contexts