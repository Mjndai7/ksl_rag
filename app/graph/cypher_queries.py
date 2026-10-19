import re

from app.db.neo4j import session
from app.graph.normalize import entity_key

_STOPWORDS = {
    "a", "about", "above", "act", "acts", "after", "all", "also", "an", "and", "any", "are", "as", "at",
    "be", "been", "being", "between", "but", "by", "can", "cap", "could", "did", "do", "does", "for",
    "from", "has", "have", "how", "if", "in", "into", "is", "it", "its", "kenya", "law", "laws", "may",
    "me", "must", "no", "not", "of", "on", "or", "other", "say", "says", "section", "shall", "should",
    "so", "such", "tell", "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "to", "under", "upon", "was", "what", "when", "where", "which", "who", "whom",
    "why", "will", "with", "within", "would", "you",
}


def query_terms(text: str) -> list[str]:
    """Keywords from a natural-language question, for the entity full-text index."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", text.lower())
    seen, terms = set(), []
    for w in words:
        if len(w) > 2 and w not in _STOPWORDS and w not in seen:
            seen.add(w)
            terms.append(w)
    return terms


def _lucene_query(terms: list[str]) -> str:
    # Terms are [a-z0-9] only, so no Lucene escaping is needed. "~" adds light fuzziness.
    return " OR ".join(f"{t} {t}~1" if len(t) > 4 else t for t in terms)


def _evidence(raw: list[str]) -> list[dict]:
    out = []
    for ev in raw or []:
        parts = ev.split("|")
        if len(parts) >= 3:
            out.append({"document_id": parts[0], "title": parts[1], "section": parts[2] or None})
    return out


class CypherQueries:
    def search_entities(self, text: str, limit: int = 8) -> list[dict]:
        terms = query_terms(text)
        if not terms:
            return []
        query = """
        CALL db.index.fulltext.queryNodes('entity_name_ft', $q) YIELD node, score
        RETURN node.name AS name, node.type AS type, node.description AS description,
               coalesce(node.doc_ids, []) AS doc_ids, score
        ORDER BY score DESC
        LIMIT $limit
        """
        with session() as s:
            return [r.data() for r in s.run(query, {"q": _lucene_query(terms), "limit": limit})]

    def search_relations(self, text: str, limit: int = 15, seed_entities: int = 6) -> list[dict]:
        """Relations around the entities that best match the question's keywords."""
        terms = query_terms(text)
        if not terms:
            return []
        query = """
        CALL db.index.fulltext.queryNodes('entity_name_ft', $q) YIELD node, score
        WITH node, score ORDER BY score DESC LIMIT $seeds
        MATCH (node)-[r]-(:Entity)
        // Only facts with provenance; pre-provenance (legacy) relations are not citable.
        WHERE size(coalesce(r.evidence, [])) > 0
        WITH node, score, r ORDER BY score DESC, size(r.evidence) DESC
        RETURN DISTINCT startNode(r).name AS source, type(r) AS relation, endNode(r).name AS target,
               node.name AS matched_entity, score, coalesce(r.evidence, []) AS evidence
        LIMIT $limit
        """
        with session() as s:
            rows = [r.data() for r in s.run(query, {"q": _lucene_query(terms), "seeds": seed_entities, "limit": limit})]
        for row in rows:
            row["evidence"] = _evidence(row["evidence"])
        return rows

    def search_entity(self, entity: str, limit: int = 20) -> list[dict]:
        """Relations of entities whose name contains the given string (used by /graph/search)."""
        query = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower($entity)
        MATCH (n)-[r]-(:Entity)
        RETURN DISTINCT startNode(r).name AS source, type(r) AS relation, endNode(r).name AS target,
               coalesce(r.evidence, []) AS evidence
        LIMIT $limit
        """
        with session() as s:
            rows = [r.data() for r in s.run(query, {"entity": entity, "limit": limit})]
        for row in rows:
            row["evidence"] = _evidence(row["evidence"])
        return rows

    def get_entity_neighborhood(self, entity: str) -> list[dict]:
        query = """
        MATCH (n:Entity)
        WHERE n.key = $key OR toLower(n.name) = toLower($name)
        MATCH (n)-[r]-(:Entity)
        RETURN DISTINCT startNode(r).name AS source, type(r) AS relation, endNode(r).name AS target,
               coalesce(r.evidence, []) AS evidence
        """
        with session() as s:
            rows = [r.data() for r in s.run(query, {"key": entity_key(entity), "name": entity.strip()})]
        for row in rows:
            row["evidence"] = _evidence(row["evidence"])
        return rows


cypher_queries = CypherQueries()
