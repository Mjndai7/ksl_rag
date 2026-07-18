from fastapi import APIRouter
from pydantic import BaseModel  

from app.retrieval.hybrid_retriever import hybrid_retriever

from app.generation.answer_engine import AnswerEngine

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@router.post("/query")
def query_docs(request: QueryRequest):
    # Step 1: Retrieve relevant contexts
    retrieval_result = hybrid_retriever.retrieve(request.query)

    # Step 2: Extract contexts from retrieval result
    merged_contexts = [
        item["text"] for item in retrieval_result["merged_contexts"]
    ]

    # Step 3: Generate answer using the retrieved contexts
    answer = AnswerEngine().answer(
        question=request.query,
        context_chunks=merged_contexts
    )

    # Step 4: Return the query results
    return {
        "query": request.query,
        "answer": answer,

        "retrieval": {
            "vector_hits": retrieval_result["vector_hits"],
            "graph_hits": retrieval_result["graph_hits"],
            "merged_contexts": retrieval_result["merged_contexts"]

        }
    }

