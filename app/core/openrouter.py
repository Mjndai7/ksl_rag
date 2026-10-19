from functools import lru_cache

from openai import OpenAI

from app.core.settings import settings


@lru_cache(maxsize=1)
def get_openrouter_client() -> OpenAI:
    """Shared OpenAI-compatible client pointed at OpenRouter (chat + embeddings)."""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY must be set to call LLM or embedding models")

    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        # The SDK retries 408/409/429/5xx with exponential backoff.
        max_retries=settings.LLM_MAX_RETRIES,
        default_headers={"X-Title": settings.APP_NAME},
    )
