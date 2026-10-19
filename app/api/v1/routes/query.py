from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.workflows.langgraph_flow import run_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)


def _sources(contexts: list[dict]) -> list[dict]:
    sources = []
    for n, item in enumerate(contexts, start=1):
        meta = item.get("metadata") or {}
        sources.append({
            "n": n,
            "type": item["source"],
            "score": item.get("score"),
            "document": meta.get("document_name"),
            "section": meta.get("section_label"),
            "link": meta.get("source_link"),
            "text": item["text"],
        })
    return sources


@router.post("/query")
def query_docs(request: QueryRequest):
    """Hybrid retrieval + grounded answer (LangGraph retrieval workflow)."""
    result = run_query(request.query)
    return {
        "query": request.query,
        "answer": result["answer"],
        "cited_sources": result["cited_sources"],
        "sources": _sources(result["merged_contexts"]),
        "warnings": result["warnings"],
        "retrieval": {
            "vector_hits": len(result["vector_hits"]),
            "graph_hits": len(result["graph_hits"]),
        },
    }


@router.post("/retrieve")
def retrieve(request: QueryRequest):
    """Retrieval only, no LLM call: useful for debugging and doesn't use LLM quota."""
    result = run_query(request.query, with_answer=False)
    return {
        "query": request.query,
        "sources": _sources(result["merged_contexts"]),
        "warnings": result["warnings"],
        "vector_hits": result["vector_hits"],
        "graph_hits": result["graph_hits"],
    }
