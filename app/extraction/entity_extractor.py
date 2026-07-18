import json
import re
import logging

from openai import OpenAI
from app.core.settings import settings

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=settings.ALIBABA_API_KEY,
    base_url=settings.ALIBABA_API_BASE
)


def _extract_json(content: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    if not content or not content.strip():
        logger.warning("Empty response from LLM")
        return {"entities": []}
    
    # Strip markdown code blocks if present
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    content = content.strip()
    
    # Try to find JSON object in the response
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nContent: {content[:500]}")
            return {"entities": []}
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}\nContent: {content[:500]}")
        return {"entities": []}


def extract_entities(text: str, max_retries: int = 3):
    """Extract entities from text with retry logic."""
    prompt = f"""
Extract entities from this text.

Return JSON:

{{
  "entities": [
    {{
      "name": "",
      "type": ""
    }}
  ]
}}

Text:
{text}
"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.ALIBABA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=settings.ALIBABA_TEMPERATURE
            )

            return _extract_json(
                response.choices[0].message.content
            )
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("All retries exhausted, returning empty entities")
                return {"entities": []}