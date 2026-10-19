from __future__ import annotations

import logging

from app.core.openrouter import get_openrouter_client
from app.core.settings import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMTruncatedError(LLMError):
    """The reply was cut off at max_tokens; `partial` holds what was generated."""

    def __init__(self, partial: str, message: str):
        super().__init__(message)
        self.partial = partial


class LLMClient:
    """Chat completions via OpenRouter, with model fallbacks for rate-limited free models."""

    def __init__(self, model: str | None = None, fallback_models: list[str] | None = None):
        self.model = model or settings.LLM_MODEL
        self.fallback_models = (
            settings.llm_fallback_models if fallback_models is None else fallback_models
        )

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Reasoning models (e.g. Nemotron) otherwise spend the whole max_tokens budget thinking
        # and return empty content.
        extra_body = {"reasoning": {"enabled": settings.LLM_REASONING}}
        if self.fallback_models:
            # OpenRouter tries these in order when the primary model errors or is rate-limited.
            extra_body["models"] = [self.model, *self.fallback_models]

        response = get_openrouter_client().chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )

        if not response.choices:
            raise RuntimeError(f"LLM returned no choices: {response}")

        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        logger.debug("LLM response from %s (%d chars, finish=%s)", response.model, len(content), choice.finish_reason)
        if not content:
            raise LLMError(f"{response.model} returned empty content (finish_reason={choice.finish_reason})")
        if choice.finish_reason == "length":
            raise LLMTruncatedError(content, f"{response.model} hit max_tokens={max_tokens}")
        return content
