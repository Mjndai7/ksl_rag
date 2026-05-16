from neo4j import GraphDatabase
from app.core.settings import settings

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
)