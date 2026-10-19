import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.chunking.splitter import Chunk, chunk_document
from app.graph.cypher_queries import cypher_queries
from app.graph.graph_algorithms import graph_algorithms
from app.graph.graph_builder import graph_builder

router = APIRouter(prefix="/graph")


class GraphSearchRequest(BaseModel):
    entity: str = Field(..., min_length=2)
    limit: int = Field(20, ge=1, le=200)


class BuildGraphRequest(BaseModel):
    text: str = Field(..., min_length=20)
    title: str = "Ad-hoc text"
    document_id: str | None = None


class BuildGraphFromChunksRequest(BaseModel):
    chunks: list[str] = Field(..., min_length=1)
    document_id: str
    title: str = "Ad-hoc chunks"


@router.post("/search")
def search_graph(request: GraphSearchRequest):
    """Relations of entities whose name contains `entity`, plus full-text entity matches."""
    return {
        "results": cypher_queries.search_entity(request.entity, limit=request.limit),
        "entities": cypher_queries.search_entities(request.entity),
    }


@router.post("/build/text")
def build_graph_from_text(request: BuildGraphRequest):
    """Extract entities/relations from raw text into the graph (uses LLM quota)."""
    document_id = request.document_id or f"adhoc-{uuid.uuid4()}"
    results = graph_builder.build_graph_for_document(
        chunks=chunk_document(request.text), document_id=document_id, title=request.title
    )
    return {"document_id": document_id, "graph_results": results}


@router.post("/build/chunks")
def build_graph_from_chunks(request: BuildGraphFromChunksRequest):
    chunks = [Chunk(index=i, text=t) for i, t in enumerate(request.chunks) if t.strip()]
    results = graph_builder.build_graph_for_document(
        chunks=chunks, document_id=request.document_id, title=request.title
    )
    return {"document_id": request.document_id, "graph_results": results}


@router.get("/stats")
def get_graph_stats():
    return {
        "stats": graph_algorithms.graph_stats(),
        "top_entities": graph_algorithms.top_connected_entities(),
        "relation_types": graph_algorithms.relationship_distribution(),
    }


@router.get("/entity/{name}")
def get_entity(name: str):
    return {"entity": name, "neighborhood": cypher_queries.get_entity_neighborhood(name)}
