from app.embeddings.embedder import embed_query
from app.graph.cypher_queries import cypher_queries
from app.vectorstore.indexing import semantic_search


class HybridRetriever:
    def __init__(self):
        self.top_k = 5
        self.graph_limit = 10

    
    def vector_retrieve(self, query: str):
        vector = embed_query(query)

        hits = semantic_search(
            query_vector=vector,
            limit=self.top_k,
        )

        contexts = []

        for hit in hits:
            contexts.append({
                "text": hit.payload.get("text", ""),
                "source": "vector",
                "score": getattr(hit, "score", None),
                "metadata": hit.payload
            })
        
        return contexts
    
    def graph_retrieve(self, query: str):
        graph_results = cypher_queries.search_entity(entity=query, limit=self.graph_limit)

        contexts = []

        for item in graph_results:
            contexts.append({
                "text": f"{item['source']} → {item['relation']} → {item['target']}",
                "source": "graph",
                "metadata": item
            })
        
        return contexts
    

    def merge_contexts(self, vector_context, graph_context):

        merged = []

        seen = set()

        def add(item):
            key = item["text"]
            if key not in seen:
                seen.add(key)
                merged.append(item)

        for v in vector_context:
            add(v)

        for g in graph_context:
            add(g)
        return merged
    
    def retrieve(self, query: str):
        vector_context = self.vector_retrieve(query)
        graph_context = self.graph_retrieve(query)

        merged_contexts = self.merge_contexts(vector_context, graph_context)

        return {
            "query": query,
            "vector_hits": vector_context,
            "graph_hits": graph_context,
            "merged_contexts": merged_contexts
        }

hybrid_retriever = HybridRetriever()
        
