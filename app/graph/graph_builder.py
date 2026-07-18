import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.graph.neo4j_client import neo4j_client
from app.extraction.knowledge_extractor import extract_knowledge

logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    A class responsible for building a knowledge graph from text data.
    """

    def build_graph_from_text(self, text: str, chunk_id: str = None, document_id: str = None):
        """
        Build a knowledge graph from the provided text.
        
        Args:
            text (str):
            chunk_id (str):
            document_id (str):
        """
        # Extract both entities and relations in a single API call
        try:
            knowledge = extract_knowledge(text)
        except Exception as e:
            logger.error(f"Failed to extract knowledge: {e}")
            knowledge = {"entities": [], "triples": []}

        # Create entities
        for e in knowledge.get("entities", []):
            try:
                neo4j_client.execute_write_query(
                    """
                    MERGE (n:Entity {name: $name})
                    SET n.type = $type
                    """,
                    {
                        "name": e["name"],
                        "type": e.get("type", "unknown")
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create entity {e.get('name', 'unknown')}: {e}")
        
        # Create relations
        for r in knowledge.get("triples", []):
            try:
                subject = r["subject"]
                relation = re.sub(r"[^A-Z0-9_]", "", r["relation"].upper().replace(" ", "_"))
                object_ = r["object"]

                neo4j_client.execute_write_query(
                    f"""
                    MERGE (a:Entity {{name: $subject}})
                    MERGE (b:Entity {{name: $object}})
                    MERGE (a)-[rel:{relation}]->(b)
                    SET rel.type = $relation
                    """,
                    {
                        "subject": subject,
                        "relation": relation,
                        "object": object_
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create relation: {e}")
        
        return {
            "entities_created": len(knowledge.get("entities", [])),
            "relations_created": len(knowledge.get("triples", [])),
            "chunk_id": chunk_id,
            "document_id": document_id
        }
    
    def build_graph_from_chunks(self, chunks: list, document_id: str, max_workers: int = 15):
        """
        Build a knowledge graph from a list of text chunks with parallel processing.
        
        Args:
            chunks (list): A list of text chunks.
            document_id (str): The ID of the document to which the chunks belong.
            max_workers (int): Number of parallel workers (default: 15).
        """
        total_chunks = len(chunks)
        
        logger.info(f"Processing {total_chunks} chunks with {max_workers} workers")
        
        results = []
        completed = 0
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {
                executor.submit(self.build_graph_from_text, chunk, str(i), document_id): i
                for i, chunk in enumerate(chunks)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_chunk):
                chunk_id = future_to_chunk[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    if completed % 10 == 0 or completed == total_chunks:
                        logger.info(f"Progress: {completed}/{total_chunks} chunks processed")
                except Exception as e:
                    logger.error(f"Chunk {chunk_id} failed: {e}")

        logger.info(f"Graph building complete: {completed} chunks processed")
        return results

graph_builder = GraphBuilder()


