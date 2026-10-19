from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.db.neo4j import ping_neo4j
from app.db.postgres import ping_postgres
from app.vectorstore.qdrant_client import COLLECTION_NAME, get_qdrant_client

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check():
    """Readiness: every backing service is reachable."""
    checks = {}

    def check(name, fn):
        try:
            fn()
            checks[name] = "ok"
        except Exception as e:
            checks[name] = f"error: {type(e).__name__}: {e}"

    check("postgres", ping_postgres)
    check("neo4j", ping_neo4j)
    check("qdrant", lambda: get_qdrant_client().get_collection(COLLECTION_NAME))
    checks["openrouter_key"] = "ok" if settings.OPENROUTER_API_KEY else "error: OPENROUTER_API_KEY not set"

    ready = all(v == "ok" for v in checks.values())
    return JSONResponse(status_code=200 if ready else 503, content={"status": "ok" if ready else "degraded", "checks": checks})
