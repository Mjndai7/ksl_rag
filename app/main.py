from fastapi import FastAPI
from app.api.v1.router import router as api_router
from app.db.init import init_neo4j
from app.vectorstore.qdrant_client import init_qdrant  

app = FastAPI(title="GraphRAG")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_qdrant()
    init_neo4j()