from app.db.neo4j import driver

class GraphAlgorithms:
    def graph_stats(self):
        """
        Calculate and return statistics about the graph.
        """
        query = """
        MATCH (n)
        WITH count(n) as total_nodes
        MATCH ()-[r]->()
        RETURN total_nodes, count(r) as total_relationships
        """

        with driver.session() as session:
            result = session.run(query).single()

            if not result:
                return {
                    "total_nodes": 0,
                    "total_relationships": 0
                }
            return {
                "total_nodes": result["total_nodes"],
                "total_relationships": result["total_relationships"]
            }
    

    def top_connected_entities(self, limit: int = 10):
        """
        Return the top N most connected entities in the graph.
        """
        query = """
        MATCH (n:Entity)-[r]-()
        RETURN n.name AS entity, count(r) AS degree
        ORDER BY degree DESC
        LIMIT $limit
        """
        with driver.session() as session:
            result = session.run(query, {"limit": limit})

            return [
                {
                    "entity": record["entity"],
                    "degree": record["degree"]
                }
                for record in result
            ]
    
    def relationship_distribution(self):
        """
        Return the distribution of relationship types in the graph.
        """
        query = """
        MATCH ()-[r]->()
        RETURN r.type AS relationship_type, count(r) AS count, type(r) AS relation
        ORDER BY count DESC
        """
        with driver.session() as session:
            result = session.run(query)

            return [
                {
                    "relationship_type": record["relationship_type"],
                    "relation": record["relation"],
                    "count": record["count"]
                }
                for record in result
            ]

graph_algorithms = GraphAlgorithms()