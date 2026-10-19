"""LangGraph workflow that answers a question.

             ┌─> vector_retrieve ─┐
    START ───┤                    ├─> merge -> generate -> END
             └─> graph_retrieve ──┘

The two retrievers run in parallel. Graph retrieval is best-effort: if Neo4j fails the
answer is still produced from vector hits, and the failure is reported in `warnings`.
"""
import logging
import operator
from typing import Annotated, List, TypedDict

from langgraph.graph import END, START, StateGraph

from app.generation.answer_engine import AnswerEngine
from app.retrieval.context_merger import merge_contexts
from app.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class RetrievalState(TypedDict, total=False):
    query: str
    with_answer: bool
    vector_hits: List[dict]
    graph_hits: List[dict]
    merged_contexts: List[dict]
    answer: str
    cited_sources: List[int]
    warnings: Annotated[List[str], operator.add]


def build_retrieval_graph(retriever: HybridRetriever | None = None, answer_engine: AnswerEngine | None = None):
    retriever = retriever or HybridRetriever()

    def vector_retrieve(state: RetrievalState) -> dict:
        return {"vector_hits": retriever.vector_retrieve(state["query"])}

    def graph_retrieve(state: RetrievalState) -> dict:
        try:
            return {"graph_hits": retriever.graph_retrieve(state["query"])}
        except Exception as e:
            logger.warning("Graph retrieval failed: %s", e)
            return {"graph_hits": [], "warnings": [f"graph retrieval failed: {e}"]}

    def merge(state: RetrievalState) -> dict:
        return {"merged_contexts": merge_contexts(state.get("vector_hits", []), state.get("graph_hits", []))}

    def generate(state: RetrievalState) -> dict:
        if not state.get("with_answer", True):
            return {}
        engine = answer_engine or AnswerEngine()
        return engine.answer(state["query"], state["merged_contexts"])

    graph = StateGraph(RetrievalState)
    graph.add_node("vector_retrieve", vector_retrieve)
    graph.add_node("graph_retrieve", graph_retrieve)
    graph.add_node("merge", merge)
    graph.add_node("generate", generate)

    graph.add_edge(START, "vector_retrieve")
    graph.add_edge(START, "graph_retrieve")
    graph.add_edge(["vector_retrieve", "graph_retrieve"], "merge")
    graph.add_edge("merge", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


retrieval_graph = build_retrieval_graph()
