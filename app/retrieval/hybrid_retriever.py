import logging

from app.core.settings import settings
from app.embeddings.embedder import embed_query
from app.graph.cypher_queries import cypher_queries
from app.retrieval.context_merger import merge_contexts
from app.vectorstore.indexing import semantic_search

logger = logging.getLogger(__name__)


def _format_evidence(evidence: list[dict]) -> str:
    refs = []
    for ev in evidence[:2]:
        ref = ev["title"].removesuffix(".pdf")
        if ev.get("section"):
            ref += f", {ev['section']}"
        refs.append(ref)
    return f" ({'; '.join(refs)})" if refs else ""


class HybridRetriever:
    def __init__(self, top_k: int | None = None, graph_limit: int | None = None):
        self.top_k = top_k or settings.VECTOR_TOP_K
        self.graph_limit = graph_limit or settings.GRAPH_TOP_K

    def vector_retrieve(self, query: str) -> list[dict]:
        hits = semantic_search(query_vector=embed_query(query), limit=self.top_k)
        return [
            {
                "text": hit.payload.get("text", ""),
                "source": "vector",
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            }
            for hit in hits
        ]

    def graph_retrieve(self, query: str) -> list[dict]:
        contexts = []
        for item in cypher_queries.search_relations(query, limit=self.graph_limit):
            relation = item["relation"].replace("_", " ").lower()
            contexts.append({
                "text": f"{item['source']} {relation} {item['target']}{_format_evidence(item['evidence'])}",
                "source": "graph",
                "score": item["score"],
                "metadata": item,
            })
        return contexts

    def retrieve(self, query: str) -> dict:
        vector_context = self.vector_retrieve(query)
        try:
            graph_context = self.graph_retrieve(query)
        except Exception as e:
            logger.warning("Graph retrieval failed, continuing with vector results only: %s", e)
            graph_context = []

        return {
            "query": query,
            "vector_hits": vector_context,
            "graph_hits": graph_context,
            "merged_contexts": merge_contexts(vector_context, graph_context),
        }


hybrid_retriever = HybridRetriever()
