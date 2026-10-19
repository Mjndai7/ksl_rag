"""Entry points to the LangGraph workflows used by the API and scripts."""
from pathlib import Path
from typing import Optional

from app.workflows.ingestion_graph import ingestion_graph, summarize
from app.workflows.retrieval_graph import retrieval_graph


def run_ingestion(
    pdf_path: str | Path,
    *,
    title: Optional[str] = None,
    source: str = "upload",
    source_id: Optional[str] = None,
    source_link: Optional[str] = None,
    extract_graph: Optional[bool] = None,
    force: bool = False,
) -> dict:
    pdf_path = Path(pdf_path)
    state = {
        "pdf_path": str(pdf_path),
        "title": title or pdf_path.name,
        "source": source,
        "source_id": source_id,
        "source_link": source_link,
        "force": force,
    }
    if extract_graph is not None:
        state["extract_graph"] = extract_graph
    return summarize(ingestion_graph.invoke(state))


def run_query(query: str, with_answer: bool = True) -> dict:
    result = retrieval_graph.invoke({"query": query, "with_answer": with_answer, "warnings": []})
    return {
        "query": query,
        "answer": result.get("answer"),
        "cited_sources": result.get("cited_sources", []),
        "warnings": result.get("warnings", []),
        "vector_hits": result.get("vector_hits", []),
        "graph_hits": result.get("graph_hits", []),
        "merged_contexts": result.get("merged_contexts", []),
    }
