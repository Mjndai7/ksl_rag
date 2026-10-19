from app.db.neo4j import session


class Neo4jClient:
    def execute_query(self, query: str, parameters: dict = None):
        with session() as s:
            return [record.data() for record in s.run(query, parameters or {})]

    def execute_write_query(self, query: str, parameters: dict = None):
        def work(tx):
            return tx.run(query, parameters or {}).consume()

        with session() as s:
            summary = s.execute_write(work)

        return {
            "nodes_created": summary.counters.nodes_created,
            "nodes_deleted": summary.counters.nodes_deleted,
            "relationships_created": summary.counters.relationships_created,
            "relationships_deleted": summary.counters.relationships_deleted,
        }

    def health_check(self) -> bool:
        try:
            with session() as s:
                return s.run("RETURN 'neo4j-ok' AS status").single()["status"] == "neo4j-ok"
        except Exception:
            return False


neo4j_client = Neo4jClient()
