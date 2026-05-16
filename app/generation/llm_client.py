from __future__ import annotations

import httpx

from app.core.settings import settings


class OpenAIClient:
    def __init__(self, api_key: str | None = None, api_base: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.api_base = api_base or settings.OPENAI_API_BASE
        self.model = model or settings.OPENAI_MODEL

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set to use the cloud LLM client")

        self.client = httpx.Client(timeout=60.0)

    def generate(self, prompt: str, temperature: float | None = None, max_tokens: int = 512) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.OPENAI_TEMPERATURE if temperature is None else temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self.client.post(f"{self.api_base}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
