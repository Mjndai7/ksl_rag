import json
import logging
import re
from typing import List

from app.chunking.splitter import Chunk
from app.generation.llm_client import LLMClient, LLMTruncatedError

logger = logging.getLogger(__name__)

ENTITY_TYPES = [
    "Act", "Section", "Part", "Schedule", "Treaty", "Institution", "Office", "Court",
    "Person", "Country", "Place", "LegalConcept", "Document", "Date",
]

_PROMPT = """You are building a knowledge graph of Kenyan statute law.
Extract the important entities and the relationships between them from the numbered excerpts below.
They come from: {title}

Rules:
- Entity types: {types}.
- Prefer specific legal entities (Acts, institutions, offices, defined terms, treaties) over generic words.
- Use the canonical full name, e.g. "Kenya Law Reform Commission", not "the Commission".
- Relation names are short UPPER_SNAKE_CASE verbs, e.g. ESTABLISHES, DEFINES, AMENDS, REPEALS,
  APPOINTS, EMPOWERS, APPLIES_TO, REFERS_TO, PART_OF, MEMBER_OF, REPORTS_TO, PUBLISHES.
- Every relation must cite the excerpt number it came from in "chunk".
- Give each entity a one-sentence "description" grounded in the text.
- Return ONLY a JSON object, no prose, in this shape:
{{"entities": [{{"name": "", "type": "", "description": ""}}],
  "relations": [{{"source": "", "relation": "", "target": "", "chunk": 0}}]}}

Excerpts:
{excerpts}
"""


def salvage_json_object(text: str) -> dict:
    """Recover a JSON object from text that is cut off or broken part-way.

    Keeps everything up to the last fully closed `{...}` and closes the open brackets,
    so a long extraction that breaks near the end still yields its complete items.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object to salvage")
    text = text[start:]

    stack, in_str, esc = [], False, False
    last_close, stack_at_close = None, None
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack:
                break
            stack.pop()
            if ch == "}":
                last_close, stack_at_close = i, list(stack)

    if last_close is None:
        raise ValueError("no complete JSON object in response")
    closing = "".join("}" if c == "{" else "]" for c in reversed(stack_at_close))
    return json.loads(text[:last_close + 1] + closing)


def parse_json_object(content: str) -> dict:
    """Extract the first JSON object from an LLM reply (handles code fences, prose, and breakage)."""
    if not content or not content.strip():
        raise ValueError("empty LLM response")
    content = re.sub(r"```(?:json)?", "", content).strip()
    # Some reasoning models wrap their thinking in tags before the answer.
    content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in response: {content[:200]!r}")
    candidate = content[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.warning("Malformed JSON from LLM (%s); salvaging items before the error", e)
        return salvage_json_object(candidate[:e.pos])


def _format_excerpts(chunks: List[Chunk]) -> str:
    parts = []
    for c in chunks:
        label = f" ({c.section_label})" if c.section_label else ""
        parts.append(f"[{c.index}]{label}\n{c.text}")
    return "\n\n".join(parts)


def extract_knowledge(
    chunks: List[Chunk],
    title: str,
    llm: LLMClient | None = None,
    max_tokens: int = 8000,
) -> dict:
    """Extract entities and relations from a batch of chunks in a single LLM call.

    Returns {"entities": [...], "relations": [...]} with each relation's "chunk" set to a
    chunk index from the batch.
    """
    llm = llm or LLMClient()
    prompt = _PROMPT.format(title=title, types=", ".join(ENTITY_TYPES), excerpts=_format_excerpts(chunks))
    try:
        data = parse_json_object(llm.generate(prompt, max_tokens=max_tokens))
    except LLMTruncatedError as e:
        logger.warning("Extraction reply truncated (%s); salvaging complete items", e)
        data = salvage_json_object(e.partial)

    valid_chunks = {c.index for c in chunks}
    default_chunk = chunks[0].index

    entities = []
    for e in data.get("entities") or []:
        if isinstance(e, dict) and str(e.get("name", "")).strip():
            entities.append({
                "name": str(e["name"]).strip(),
                "type": str(e.get("type") or "Unknown").strip(),
                "description": str(e.get("description") or "").strip(),
            })

    relations = []
    for r in data.get("relations") or data.get("triples") or []:
        if not isinstance(r, dict):
            continue
        source = str(r.get("source") or r.get("subject") or "").strip()
        target = str(r.get("target") or r.get("object") or "").strip()
        relation = str(r.get("relation") or "").strip()
        if not (source and target and relation):
            continue
        try:
            chunk = int(r.get("chunk"))
        except (TypeError, ValueError):
            chunk = default_chunk
        relations.append({
            "source": source,
            "relation": relation,
            "target": target,
            "chunk": chunk if chunk in valid_chunks else default_chunk,
        })

    return {"entities": entities, "relations": relations}
