import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as api_router
from app.db.neo4j import close_neo4j, init_neo4j
from app.vectorstore.qdrant_client import init_qdrant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
# httpx logs every OpenRouter/Qdrant request at INFO.
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_qdrant()
    init_neo4j()
    yield
    close_neo4j()


app = FastAPI(title="GraphRAG", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")
