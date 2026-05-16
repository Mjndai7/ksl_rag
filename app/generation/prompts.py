BASE_QA_PROMPT = '''You are a helpful assistant. Use the provided context to answer the question.
If the context is not enough, say you don't know rather than invent an answer.

Context:
{context}

Question:
{question}
'''


def build_qa_prompt(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(chunk.strip() for chunk in context_chunks if chunk).strip()
    if not context:
        context = "No relevant context is available."
    return BASE_QA_PROMPT.format(question=question.strip(), context=context)
