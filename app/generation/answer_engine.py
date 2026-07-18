from __future__ import annotations

from app.generation.llm_client import AlibabaClient
from app.generation.prompts import build_qa_prompt


class AnswerEngine:
    def __init__(self, llm_client: AlibabaClient | None = None):
        self.llm_client = llm_client or AlibabaClient()

    def answer(self, question: str, context_chunks: list[str], temperature: float = 0.0, max_tokens: int = 512) -> str:
        prompt = build_qa_prompt(question, context_chunks)
        return self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
