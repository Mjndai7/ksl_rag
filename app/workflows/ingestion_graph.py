"""LangGraph workflow that ingests one PDF.

parse -> check_duplicate -> register -> chunk -> embed -> index -> build_graph -> finalize

Any node that fails sets `error`, and the graph routes to `fail`, which marks the document
failed in Postgres. A duplicate routes straight to END with `status="skipped"`.
"""
import hashlib
import logging
import time
from typing import Any, Callable, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.chunking.splitter import Chunk, chunk_document
from app.core.settings import settings
from app.db import repository
from app.embeddings.embedder import embed_chunks
from app.graph.graph_builder import graph_builder
from app.parser.cleaners import clean_text
from app.parser.pdf_parser import parse_pdf
from app.vectorstore.indexing import upsert_chunks

logger = logging.getLogger(__name__)


class IngestionState(TypedDict, total=False):
    # inputs
    pdf_path: str
    title: str
    source: str
    source_id: Optional[str]
    source_link: Optional[str]
    extract_graph: bool
    force: bool
    # produced along the way
    text: str
    checksum: str
    document_id: Optional[str]
    chunks: List[Chunk]
    vectors: List[List[float]]
    graph: dict
    timings: dict
    status: str  # completed | skipped | failed
    reason: str
    error: str
    failed_step: str


def _timed(name: str, fn: Callable[[IngestionState], dict]) -> Callable[[IngestionState], dict]:
    """Wrap a node: record its duration and turn exceptions into an `error` state update."""

    def node(state: IngestionState) -> dict:
        start = time.time()
        try:
            update = fn(state) or {}
        except Exception as e:
            logger.exception("[INGEST] %s failed at %s", state.get("title"), name)
            update = {"error": f"{type(e).__name__}: {e}", "failed_step": name}
        timings = {**state.get("timings", {}), name: round(time.time() - start, 2)}
        return {**update, "timings": timings}

    return node


def parse(state: IngestionState) -> dict:
    text = clean_text(parse_pdf(state["pdf_path"]))
    if not text.strip():
        raise ValueError("PDF contains no extractable text (scanned images need OCR)")
    return {"text": text, "checksum": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def check_duplicate(state: IngestionState) -> dict:
    existing = repository.find_document(state["checksum"], state.get("source_id"))
    if existing is None:
        return {"document_id": None}

    up_to_date = (
        existing["checksum"] == state["checksum"]
        and existing["status"] == "completed"
        and existing["embedding_model"] == settings.EMBEDDING_MODEL
    )
    if up_to_date and not state.get("force"):
        return {
            "document_id": existing["id"],
            "status": "skipped",
            "reason": "already ingested with the current embedding model",
        }
    # Same file re-uploaded/updated, or a previous run failed: reprocess under the same id
    # so its old vectors and graph facts are replaced rather than duplicated.
    return {"document_id": existing["id"]}


def register(state: IngestionState) -> dict:
    document_id = repository.upsert_document_processing(
        state.get("document_id"),
        title=state["title"],
        source=state["source"],
        source_id=state.get("source_id"),
        source_link=state.get("source_link"),
        checksum=state["checksum"],
        content=state["text"],
        embedding_model=settings.EMBEDDING_MODEL,
    )
    return {"document_id": document_id}


def chunk(state: IngestionState) -> dict:
    chunks = chunk_document(state["text"])
    if not chunks:
        raise ValueError("chunking produced no chunks")
    return {"chunks": chunks}


def embed(state: IngestionState) -> dict:
    # Prefix the title/section so the embedding knows which statute a passage is from.
    inputs = [
        f"{state['title'].removesuffix('.pdf')}{' ' + c.section_label if c.section_label else ''}\n{c.text}"
        for c in state["chunks"]
    ]
    return {"vectors": embed_chunks(inputs)}


def index(state: IngestionState) -> dict:
    upsert_chunks(
        chunks=state["chunks"],
        embeddings=state["vectors"],
        metadata={
            "document_id": state["document_id"],
            "document_name": state["title"],
            "source": state["source"],
            "source_id": state.get("source_id"),
            "source_link": state.get("source_link"),
        },
    )
    return {}


def build_graph(state: IngestionState) -> dict:
    if not state.get("extract_graph", settings.GRAPH_EXTRACTION_ENABLED):
        return {"graph": {"skipped": True}}
    return {
        "graph": graph_builder.build_graph_for_document(
            chunks=state["chunks"],
            document_id=state["document_id"],
            title=state["title"],
        )
    }


def finalize(state: IngestionState) -> dict:
    graph = state.get("graph") or {}
    repository.update_document(
        state["document_id"],
        status="completed",
        chunk_count=len(state["chunks"]),
        entity_count=graph.get("entities"),
        relation_count=graph.get("relations"),
    )
    logger.info("[INGEST] %s completed: %d chunks, graph=%s", state["title"], len(state["chunks"]), graph)
    return {"status": "completed"}


def fail(state: IngestionState) -> dict:
    if state.get("document_id"):
        try:
            repository.update_document(state["document_id"], status="failed", error=state.get("error"))
        except Exception:
            logger.exception("Could not mark document %s failed", state["document_id"])
    return {"status": "failed"}


_STEPS = [
    ("parse", parse),
    ("check_duplicate", check_duplicate),
    ("register", register),
    ("chunk", chunk),
    ("embed", embed),
    ("index", index),
    ("build_graph", build_graph),
    ("finalize", finalize),
]


def build_ingestion_graph():
    graph = StateGraph(IngestionState)
    for name, fn in _STEPS:
        graph.add_node(name, _timed(name, fn))
    graph.add_node("fail", fail)

    graph.add_edge(START, "parse")
    for (name, _), (next_name, _) in zip(_STEPS, _STEPS[1:]):
        def route(state: IngestionState, _next: str = next_name) -> str:
            if state.get("error"):
                return "fail"
            if state.get("status") == "skipped":
                return END
            return _next

        graph.add_conditional_edges(name, route, [next_name, "fail", END])

    graph.add_conditional_edges("finalize", lambda s: "fail" if s.get("error") else END, ["fail", END])
    graph.add_edge("fail", END)
    return graph.compile()


ingestion_graph = build_ingestion_graph()


def summarize(state: dict[str, Any]) -> dict:
    """JSON-safe summary of a finished ingestion run."""
    return {
        "title": state.get("title"),
        "document_id": state.get("document_id"),
        "status": state.get("status"),
        "reason": state.get("reason"),
        "error": state.get("error"),
        "failed_step": state.get("failed_step"),
        "chunks": len(state.get("chunks") or []),
        "graph": state.get("graph"),
        "timings": state.get("timings"),
    }
