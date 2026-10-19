import logging

from neo4j import GraphDatabase

from app.core.settings import settings

logger = logging.getLogger(__name__)

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
    # Schema-hint warnings ("property not available") are noise on a fresh graph.
    notifications_min_severity="OFF",
)

_SCHEMA = [
    "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE",
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
    "CREATE FULLTEXT INDEX entity_name_ft IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.description]",
]


def session():
    return driver.session(database=settings.NEO4J_DATABASE)


def init_neo4j():
    """Verify connectivity and create constraints/indexes used by the graph layer."""
    driver.verify_connectivity()
    with session() as s:
        # Entities written before keys existed: backfill so they stay searchable.
        s.run(
            "MATCH (e:Entity) WHERE e.key IS NULL AND e.name IS NOT NULL "
            "SET e.key = toLower(trim(e.name)) + '#legacy-' + elementId(e)"
        ).consume()
        for stmt in _SCHEMA:
            try:
                s.run(stmt).consume()
            except Exception as e:
                logger.warning("Neo4j schema statement failed (%s): %s", stmt, e)


def ping_neo4j() -> None:
    driver.verify_connectivity()


def close_neo4j():
    """Closes the Neo4j driver connection pool."""
    driver.close()
