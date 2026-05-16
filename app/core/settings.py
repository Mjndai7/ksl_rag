from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    APP_NAME: str = "GraphRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # PostgreSQL
    POSTGRES_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # Qdrant
    QDRANT_URL: str
    QDRANT_COLLECTION: str = "documents"
    QDRANT_VECTOR_SIZE: int = 384
    QDRANT_DISTANCE: str = "Cosine"

    # Neo4j
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50


    # Google Drive
    GOOGLE_CREDENTIALS_PATH: str
    GOOGLE_DRIVE_FOLDER_ID: str

    # Cloud LLM settings
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()