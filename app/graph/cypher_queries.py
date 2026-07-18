from app.db.neo4j import driver

class CypherQueries:
    def search_entity(self, entity: str, limit: int = 20):
        """
        Search for an entity in the graph and return its relationships.
        """
        query = """
        MATCH (n:Entity)-[r]-(m:Entity)
        WHERE toLower(n.name) CONTAINS toLower($entity)
           OR toLower(m.name) CONTAINS toLower($entity)
        
        RETURN n.name AS source, type(r) AS relation, m.name AS target, r.type AS relation_type
        LIMIT $limit
        """
        with driver.session() as session:
            result = session.run(
                query,
                {
                    "entity": entity,
                    "limit": limit
                }
            )
            return [
                {
                    "source": record["source"],
                    "relation": record["relation"],
                    "target": record["target"],
                    "relation_type": record["relation_type"]
                }
                for record in result
            ]
    
    def get_entity_neighborhood(self, entity: str):
        """
        Get the neighborhood of an entity, including directly connected nodes and relationships.
        """

        query = """
        MATCH (n:Entity)-[r]-(m:Entity)
        WHERE n.name = $entity
        
        RETURN n.name AS source, type(r) AS relation, m.name AS target, r.type AS relation_type
        """

        with driver.session() as session:
            result = session.run(
                query,
                {
                    "entity": entity
                }
            )
            return list(result)
    
cypher_queries = CypherQueries()
