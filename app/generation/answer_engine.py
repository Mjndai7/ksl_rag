from __future__ import annotations

import re

from app.core.settings import settings
from app.generation.llm_client import LLMClient
from app.generation.prompts import SYSTEM_PROMPT, build_qa_prompt


def cited_source_numbers(answer: str, n_sources: int) -> list[int]:
    """Source numbers the answer actually cites, e.g. "[1][3]" -> [1, 3]."""
    nums = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return sorted(n for n in nums if 1 <= n <= n_sources)


class AnswerEngine:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def answer(self, question: str, contexts: list[dict], max_tokens: int | None = None) -> dict:
        if not contexts:
            return {
                "answer": "I don't know based on the available statutes: no relevant sources were found.",
                "cited_sources": [],
            }
        prompt = build_qa_prompt(question, contexts)
        text = self.llm_client.generate(
            prompt,
            system=SYSTEM_PROMPT,
            max_tokens=max_tokens or settings.ANSWER_MAX_TOKENS,
        )
        return {"answer": text, "cited_sources": cited_source_numbers(text, len(contexts))}
