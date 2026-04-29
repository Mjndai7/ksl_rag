from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GraphRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # PostgreSQL
    POSTGRES_URL: str

    # Qdrant
    QDRANT_URL: str
    QDRANT_COLLECTION: str = "documents"

    # Neo4j
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # Google Drive
    GOOGLE_CREDENTIALS_JSON: str
    GOOGLE_DRIVE_FOLDER_ID: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()