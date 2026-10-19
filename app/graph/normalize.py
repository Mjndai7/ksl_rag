import re

_LEADING_ARTICLE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
_RESERVED_TYPES = {"MENTIONED_IN"}


def entity_key(name: str) -> str:
    """Canonical key used to merge entity mentions: case/space/punctuation-insensitive."""
    key = re.sub(r"\s+", " ", name).strip().strip(".,;:\"'“”‘’()")
    key = _LEADING_ARTICLE.sub("", key)
    return key.lower()


def relation_type(relation: str) -> str:
    """Turn free-text relation names into safe Neo4j relationship types."""
    t = re.sub(r"[\s\-/]+", "_", relation.strip().upper())
    t = re.sub(r"[^A-Z0-9_]", "", t)
    t = re.sub(r"_+", "_", t).strip("_")[:60]
    if not t:
        return "RELATED_TO"
    if t[0].isdigit():
        t = f"R_{t}"
    if t in _RESERVED_TYPES:
        t = f"{t}_REL"
    return t
