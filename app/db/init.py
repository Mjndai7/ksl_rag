from qdrant_client.models import Distance, VectorParams
from app.core.settings import settings
from app.db.neo4j import driver


def init_neo4j():
    with driver.session() as session:
        session.run("RETURN 1")