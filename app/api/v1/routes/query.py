from fastapi import APIRouter
from pydantic import BaseModel  

from app.retrieval.hybrid_retriever import retrieve
from app.generation.answer_engine import AnswerEngine

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def query_docs(request: QueryRequest):
    # Step 1: Retrieve relevant contexts
    contexts = retrieve(request.query)

    # Step 2: Generate answer using the retrieved contexts
    answer = AnswerEngine().answer(request.query, contexts)

    return {
        "query": request.query,
        "answer": answer,
        "contexts": contexts
    }

