from fastapi import APIRouter
from pydantic import BaseModel
import uuid

from app.graph.cypher_queries import cypher_queries
from app.graph.graph_algorithms import graph_algorithms
from app.graph.graph_builder import graph_builder


router = APIRouter(prefix="/graph")

class GraphSearchRequest(BaseModel):
    entity: str

class BuildGraphRequest(BaseModel):
    text: str

class BuildGraphFromChunksRequest(BaseModel):
    chunks: list[str]
    document_id: str

@router.post("/search")
def search_graph(request: GraphSearchRequest):
    results = cypher_queries.search_entity(request.entity)
    return {"results": results}

@router.post("/build/text")
def build_graph_from_text(request: BuildGraphRequest):
    # Generate unique IDs for tracking
    chunk_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    
    graph_results = graph_builder.build_graph_from_text(
        text=request.text,
        chunk_id=chunk_id,
        document_id=document_id
    )
    return {"graph_results": graph_results}

@router.post("/build/chunks")
def build_graph_from_chunks(request: BuildGraphFromChunksRequest):
    graph_results = graph_builder.build_graph_from_chunks(
        chunks=request.chunks,
        document_id=request.document_id
    )
    return {"graph_results": graph_results}

@router.get("/stats")
def get_graph_stats():
    stats = graph_algorithms.graph_stats()
    return {"stats": stats}

