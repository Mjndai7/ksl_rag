from fastapi import APIRouter

from app.api.v1.routes import (
    documents,
    graph,
    health,
    ingest,
    query,
)

router = APIRouter()

router.include_router(ingest.router)
router.include_router(query.router)
router.include_router(health.router)
router.include_router(graph.router)
router.include_router(documents.router)
