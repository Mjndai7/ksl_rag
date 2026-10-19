from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "GraphRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # PostgreSQL
    POSTGRES_URL: str

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "ksl_chunks"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50

    # Google Drive (only needed for /ingest from Drive)
    GOOGLE_CREDENTIALS_PATH: str | None = None
    GOOGLE_DRIVE_FOLDER_ID: str | None = None
    DOWNLOAD_DIR: str = "data/raw"

    # OpenRouter (OpenAI-compatible API)
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Primary chat model; fallbacks are tried by OpenRouter when it is rate-limited or down.
    LLM_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    LLM_FALLBACK_MODELS: str = "google/gemma-4-31b-it:free,nvidia/nemotron-3.5-lightning:free"
    LLM_TEMPERATURE: float = 0.0
    # Free reasoning models burn max_tokens on hidden reasoning (empty replies) unless disabled.
    LLM_REASONING: bool = False
    LLM_MAX_RETRIES: int = 4
    LLM_TIMEOUT_SECONDS: float = 180.0
    ANSWER_MAX_TOKENS: int = 1024

    EMBEDDING_MODEL: str = "nvidia/nemotron-3-embed-1b:free"
    EMBEDDING_DIM: int = 2048
    EMBEDDING_BATCH_SIZE: int = 16

    # Chunking
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    # Graph extraction: chunks are packed into one LLM call up to this many characters,
    # which keeps ingestion inside free-tier daily request limits.
    GRAPH_EXTRACTION_ENABLED: bool = True
    GRAPH_BATCH_CHARS: int = 16000
    GRAPH_MAX_WORKERS: int = 2

    # Retrieval
    VECTOR_TOP_K: int = 6
    GRAPH_TOP_K: int = 15

    @property
    def llm_fallback_models(self) -> list[str]:
        return [m.strip() for m in self.LLM_FALLBACK_MODELS.split(",") if m.strip()]


settings = Settings()
