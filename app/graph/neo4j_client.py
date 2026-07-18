from app.db.neo4j import driver


class Neo4jClient:
    def execute_query(self, query: str, parameters: dict = None):
        with driver.session() as session:
            result = session.run(query, parameters) 

            return list(result)
    
    def execute_write_query(self, query: str, parameters: dict = None):
        with driver.session() as session:

            result = session.run(query, parameters)
            summary = result.consume()

            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
            }
    
    def health_check(self) -> bool:
        try:
            with driver.session() as session:
                result = session.run(
                    "RETURN 'neo4j-ok' as status"
                )
                return result.single()["status"] == "neo4j-ok"
            return True
        except Exception as e:
            print(f"Neo4j health check failed: {e}")
            return False

neo4j_client = Neo4jClient()

        