from __future__ import annotations

from openai import OpenAI
from app.core.settings import settings


class AlibabaClient:
    def __init__(self, api_key: str | None = None, api_base: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.ALIBABA_API_KEY
        self.api_base = api_base or settings.ALIBABA_API_BASE
        self.model = model or settings.ALIBABA_MODEL

        if not self.api_key:
            raise ValueError("ALIBABA_API_KEY must be set to use the cloud LLM client")

        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    def generate(self, prompt: str, temperature: float | None = None, max_tokens: int = 512) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.ALIBABA_TEMPERATURE if temperature is None else temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
