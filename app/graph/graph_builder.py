import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from app.chunking.splitter import Chunk
from app.core.settings import settings
from app.extraction.knowledge_extractor import extract_knowledge
from app.graph.neo4j_client import neo4j_client
from app.graph.normalize import entity_key, relation_type

logger = logging.getLogger(__name__)


def batch_chunks(chunks: List[Chunk], max_chars: int) -> List[List[Chunk]]:
    """Pack consecutive chunks into batches of at most max_chars (one LLM call each)."""
    batches: List[List[Chunk]] = []
    current: List[Chunk] = []
    size = 0
    for c in chunks:
        if current and size + len(c.text) > max_chars:
            batches.append(current)
            current, size = [], 0
        current.append(c)
        size += len(c.text)
    if current:
        batches.append(current)
    return batches


class GraphBuilder:
    """Builds the knowledge graph for a document: LLM extraction, then batched Neo4j writes."""

    def delete_document_graph(self, document_id: str) -> None:
        """Remove a document's contribution so re-ingestion does not double count."""
        neo4j_client.execute_write_query(
            """
            MATCH (:Entity)-[r]->(:Entity)
            WHERE any(ev IN coalesce(r.evidence, []) WHERE ev STARTS WITH $prefix)
            SET r.evidence = [ev IN r.evidence WHERE NOT ev STARTS WITH $prefix],
                r.doc_ids = [d IN coalesce(r.doc_ids, []) WHERE d <> $doc_id]
            WITH r WHERE size(r.doc_ids) = 0
            DELETE r
            """,
            {"doc_id": document_id, "prefix": f"{document_id}|"},
        )
        neo4j_client.execute_write_query(
            """
            MATCH (e:Entity)-[m:MENTIONED_IN]->(:Document {id: $doc_id})
            DELETE m
            WITH DISTINCT e
            SET e.doc_ids = [d IN coalesce(e.doc_ids, []) WHERE d <> $doc_id]
            WITH e WHERE size(e.doc_ids) = 0 AND NOT (e)--()
            DELETE e
            """,
            {"doc_id": document_id},
        )

    def write_knowledge(self, knowledge: dict, chunks: List[Chunk], document_id: str, title: str) -> dict:
        by_index = {c.index: c for c in chunks}

        entities = {}
        for e in knowledge.get("entities", []):
            key = entity_key(e["name"])
            if key:
                entities.setdefault(key, {"key": key, **e})
        for r in knowledge.get("relations", []):
            for name in (r["source"], r["target"]):
                key = entity_key(name)
                if key and key not in entities:
                    entities[key] = {"key": key, "name": name, "type": "Unknown", "description": ""}

        neo4j_client.execute_write_query(
            """
            MERGE (d:Document {id: $doc_id})
            SET d.title = $title
            WITH d
            UNWIND $entities AS e
            MERGE (n:Entity {key: e.key})
            ON CREATE SET n.name = e.name, n.type = e.type, n.description = e.description
            SET n.description = CASE WHEN coalesce(n.description, '') = '' THEN e.description ELSE n.description END,
                n.type = CASE WHEN coalesce(n.type, 'Unknown') = 'Unknown' THEN e.type ELSE n.type END,
                n.doc_ids = CASE WHEN $doc_id IN coalesce(n.doc_ids, []) THEN n.doc_ids
                                 ELSE coalesce(n.doc_ids, []) + $doc_id END
            MERGE (n)-[:MENTIONED_IN]->(d)
            """,
            {"doc_id": document_id, "title": title, "entities": list(entities.values())},
        )

        grouped = defaultdict(list)
        for r in knowledge.get("relations", []):
            src, tgt = entity_key(r["source"]), entity_key(r["target"])
            if not src or not tgt or src == tgt:
                continue
            chunk = by_index.get(r["chunk"])
            section = chunk.section_label if chunk and chunk.section_label else ""
            grouped[relation_type(r["relation"])].append({
                "source_key": src,
                "target_key": tgt,
                "evidence": f"{document_id}|{title}|{section}|{r['chunk']}",
            })

        relation_count = 0
        for rel_type, rels in grouped.items():
            # Relationship types can't be parameterised; rel_type is sanitised to [A-Z0-9_].
            neo4j_client.execute_write_query(
                f"""
                UNWIND $rels AS r
                MATCH (a:Entity {{key: r.source_key}})
                MATCH (b:Entity {{key: r.target_key}})
                MERGE (a)-[x:`{rel_type}`]->(b)
                SET x.type = $rel_type,
                    x.doc_ids = CASE WHEN $doc_id IN coalesce(x.doc_ids, []) THEN x.doc_ids
                                     ELSE coalesce(x.doc_ids, []) + $doc_id END,
                    x.evidence = CASE WHEN r.evidence IN coalesce(x.evidence, []) THEN x.evidence
                                      ELSE coalesce(x.evidence, []) + r.evidence END
                """,
                {"rels": rels, "rel_type": rel_type, "doc_id": document_id},
            )
            relation_count += len(rels)

        return {"entities": len(entities), "relations": relation_count}

    def _process_batch(self, batch: List[Chunk], document_id: str, title: str, split_on_failure: bool = True) -> dict:
        try:
            knowledge = extract_knowledge(batch, title=title)
        except Exception as e:
            if split_on_failure and len(batch) > 1:
                logger.warning("Extraction failed for %d-chunk batch (%s); retrying as two halves", len(batch), e)
                mid = len(batch) // 2
                left = self._process_batch(batch[:mid], document_id, title, split_on_failure=False)
                right = self._process_batch(batch[mid:], document_id, title, split_on_failure=False)
                return {
                    "entities": left["entities"] + right["entities"],
                    "relations": left["relations"] + right["relations"],
                    "failed_batches": left["failed_batches"] + right["failed_batches"],
                }
            logger.error("Extraction failed for chunks %s: %s", [c.index for c in batch], e)
            return {"entities": 0, "relations": 0, "failed_batches": 1}

        written = self.write_knowledge(knowledge, batch, document_id, title)
        return {**written, "failed_batches": 0}

    def build_graph_for_document(
        self,
        chunks: List[Chunk],
        document_id: str,
        title: str,
        max_workers: int | None = None,
        batch_chars: int | None = None,
    ) -> dict:
        max_workers = max_workers or settings.GRAPH_MAX_WORKERS
        batches = batch_chunks(chunks, batch_chars or settings.GRAPH_BATCH_CHARS)
        logger.info("[GRAPH] %s: %d chunks in %d extraction batches", title, len(chunks), len(batches))

        self.delete_document_graph(document_id)

        totals = {"entities": 0, "relations": 0, "batches": len(batches), "failed_batches": 0}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._process_batch, b, document_id, title) for b in batches]
            for done, future in enumerate(as_completed(futures), start=1):
                try:
                    result = future.result()
                except Exception as e:
                    logger.error("Graph batch failed while writing to Neo4j: %s", e)
                    totals["failed_batches"] += 1
                    continue
                for k in ("entities", "relations", "failed_batches"):
                    totals[k] += result[k]
                logger.info("[GRAPH] %s: batch %d/%d done", title, done, len(batches))

        return totals


graph_builder = GraphBuilder()
