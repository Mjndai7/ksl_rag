from neo4j import GraphDatabase
from app.core.settings import settings

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
)

def init_neo4j():
    """
    Verifies the connection to the Neo4j database by running a simple query.
    """
    with driver.session() as session:
        session.run("RETURN 1")


def close_neo4j():
    """
    Closes the Neo4j driver connection pool.
    """
    driver.close()

    