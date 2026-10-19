from app.db.neo4j import session


class GraphAlgorithms:
    def graph_stats(self) -> dict:
        query = """
        CALL { MATCH (n) RETURN count(n) AS total_nodes }
        CALL { MATCH ()-[r]->() RETURN count(r) AS total_relationships }
        CALL { MATCH (e:Entity) RETURN count(e) AS entities }
        CALL { MATCH (d:Document) RETURN count(d) AS documents }
        RETURN total_nodes, total_relationships, entities, documents
        """
        with session() as s:
            return s.run(query).single().data()

    def top_connected_entities(self, limit: int = 10) -> list[dict]:
        query = """
        MATCH (n:Entity)-[r]-(:Entity)
        RETURN n.name AS entity, n.type AS type, count(r) AS degree
        ORDER BY degree DESC
        LIMIT $limit
        """
        with session() as s:
            return [r.data() for r in s.run(query, {"limit": limit})]

    def relationship_distribution(self, limit: int = 20) -> list[dict]:
        query = """
        MATCH (:Entity)-[r]->(:Entity)
        RETURN type(r) AS relation, count(r) AS count
        ORDER BY count DESC
        LIMIT $limit
        """
        with session() as s:
            return [r.data() for r in s.run(query, {"limit": limit})]


graph_algorithms = GraphAlgorithms()
