from fastapi import APIRouter

from app.api.v1.routes import (
    ingest,
    query,
    health,
)

router = APIRouter()

router.include_router(ingest.router)
router.include_router(query.router)
router.include_router(health.router)