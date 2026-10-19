from fastapi import APIRouter, HTTPException

from app.db import repository
from app.graph.graph_builder import graph_builder
from app.vectorstore.indexing import delete_document_points

router = APIRouter(prefix="/documents")


@router.get("")
def list_documents():
    return {"documents": repository.list_documents()}


@router.get("/{document_id}")
def get_document(document_id: str):
    doc = repository.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Remove a document's vectors, graph facts and metadata."""
    doc = repository.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_points(doc["id"])
    graph_builder.delete_document_graph(doc["id"])
    repository.delete_document_row(doc["id"])
    return {"deleted": doc["id"], "title": doc["title"]}
