import logging
from fastapi import FastAPI
from app.api.v1.router import router as api_router
from app.db.neo4j import init_neo4j, close_neo4j
from app.vectorstore.qdrant_client import init_qdrant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

app = FastAPI(title="GraphRAG")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_qdrant()
    init_neo4j()


@app.on_event("shutdown")
def shutdown_event():
    close_neo4j()