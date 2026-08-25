# GraphRAG - Hybrid Retrieval-Augmented Generation Engine

A production-grade GraphRAG system that combines vector search, knowledge graphs, and LLM-powered answer generation. The engine ingests PDFs from Google Drive, builds semantic embeddings and knowledge graphs, and answers queries using hybrid retrieval.

## Overview

GraphRAG implements a three-stage pipeline:

1. **Ingestion**: Download PDFs → Parse → Chunk → Embed → Index → Extract Knowledge → Build Graph
2. **Retrieval**: Hybrid search combining vector similarity (Qdrant) and graph traversal (Neo4j)
3. **Generation**: LLM-powered answer synthesis using retrieved context

The system uses **Alibaba Model Studio** for both embeddings (`text-embedding-v4`) and LLM inference (`qwen3.6-flash`), providing cloud-native AI capabilities without local model hosting.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  FastAPI + Pydantic Models + Route Handlers                     │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Ingestion   │    │   Retrieval  │    │  Generation  │
│   Pipeline   │    │   Pipeline   │    │   Pipeline   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    Database Layer                             │
│  PostgreSQL (metadata) │ Qdrant (vectors) │ Neo4j (graph)   │
└──────────────────────────────────────────────────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   External Services                           │
│  Google Drive │ Alibaba Model Studio (LLM + Embeddings)     │
└──────────────────────────────────────────────────────────────┘
```

## Features

### Core Capabilities

- **PDF Ingestion**: Automatic download and processing of PDFs from Google Drive folders
- **Semantic Chunking**: Fixed-size chunking with configurable overlap (default: 1200 chars, 200 overlap)
- **Vector Embeddings**: Cloud-based embeddings using Alibaba's `text-embedding-v4` (1024 dimensions)
- **Knowledge Graph**: Automatic entity and relation extraction using LLM
- **Hybrid Retrieval**: Combines vector similarity search with graph-based entity search
- **RAG Answer Generation**: LLM-powered answers with context grounding
- **Deduplication**: SHA-256 checksums prevent reprocessing the same document
- **Parallel Processing**: 15 concurrent workers for graph building

### Implemented Features

✅ **Ingestion Pipeline**
- Google Drive integration with service account authentication
- PDF parsing using PyMuPDF
- Text chunking with overlap
- Batch embedding (10 chunks per API call)
- Vector indexing in Qdrant
- Knowledge extraction (entities + relations in single LLM call)
- Graph building with parallel processing
- Metadata storage in PostgreSQL
- Document deduplication via checksums

✅ **Retrieval Pipeline**
- Vector search (top-5 results)
- Graph search (top-10 entity matches)
- Context merging with deduplication
- Hybrid retrieval combining both approaches

✅ **Generation Pipeline**
- RAG prompt construction
- LLM answer generation using Alibaba Model Studio
- Context-grounded responses (refuses to answer if context insufficient)

✅ **API Endpoints**
- Health check
- Document ingestion
- Query with hybrid retrieval
- Graph search
- Graph building from text/chunks
- Graph statistics

✅ **Database Integration**
- PostgreSQL for metadata and deduplication
- Qdrant for vector storage and similarity search
- Neo4j for knowledge graph storage and traversal

## Layer Overview

### 1. API Layer (`app/api/`)

**Purpose**: HTTP interface for the GraphRAG engine

**Components**:
- `main.py`: FastAPI application with startup/shutdown hooks
- `router.py`: Route aggregation
- `routes/`: Individual endpoint handlers
  - `health.py`: Liveness probe
  - `ingest.py`: Document ingestion trigger
  - `query.py`: Hybrid retrieval + answer generation
  - `graph.py`: Direct graph operations

**Key Endpoints**:
```
GET  /api/v1/health              - Health check
POST /api/v1/ingest              - Ingest PDFs from Google Drive
POST /api/v1/query               - Query with hybrid retrieval
POST /api/v1/graph/search        - Search entities in graph
POST /api/v1/graph/build/text    - Build graph from text
POST /api/v1/graph/build/chunks  - Build graph from chunks
GET  /api/v1/graph/stats         - Get graph statistics
```

### 2. Configuration Layer (`app/core/`)

**Purpose**: Centralized configuration management

**Components**:
- `settings.py`: Pydantic Settings for environment variables
- `logging.py`: Logging configuration

**Configuration Sources**:
- Environment variables
- `.env` file (loaded automatically)
- Default values for optional settings

### 3. Database Layer (`app/db/`)

**Purpose**: Data persistence and retrieval

**Components**:
- `models.py`: SQLAlchemy models (Document)
- `postgres.py`: PostgreSQL connection and session management
- `neo4j.py`: Neo4j driver initialization

**Databases**:
- **PostgreSQL**: Document metadata, checksums for deduplication
- **Neo4j**: Knowledge graph (entities and relationships)
- **Qdrant**: Vector embeddings for semantic search

### 4. Ingestion Layer (`app/ingestion/`, `app/parser/`, `app/chunking/`, `app/embeddings/`, `app/extraction/`, `app/graph/`)

**Purpose**: Document processing pipeline

**Components**:
- `drive_client.py`: Google Drive API integration
- `pdf_parser.py`: PDF text extraction using PyMuPDF
- `splitter.py`: Text chunking strategies
- `embedder.py`: Vector embedding using Alibaba API
- `knowledge_extractor.py`: Entity and relation extraction
- `graph_builder.py`: Knowledge graph construction
- `sync_service.py`: Orchestration of ingestion pipeline

**Pipeline Flow**:
```
Google Drive → Download → Parse PDF → Chunk Text → Embed → Index in Qdrant
                                                    ↓
                                          Extract Knowledge → Build Graph in Neo4j
                                                    ↓
                                          Store Metadata in PostgreSQL
```

### 5. Retrieval Layer (`app/retrieval/`)

**Purpose**: Hybrid search combining vector and graph retrieval

**Components**:
- `hybrid_retriever.py`: Orchestrates vector + graph search
- `context_merger.py`: Merges and deduplicates contexts
- `reranker.py`: (Placeholder for future reranking)

**Retrieval Strategy**:
1. **Vector Search**: Embed query → Search Qdrant → Return top-5 chunks
2. **Graph Search**: Search entities in Neo4j → Return top-10 relationships
3. **Merge**: Combine results, deduplicate by text content
4. **Prioritize**: Vector results first, then graph results

### 6. Generation Layer (`app/generation/`)

**Purpose**: LLM-powered answer synthesis

**Components**:
- `llm_client.py`: Alibaba Model Studio API client
- `answer_engine.py`: Answer generation orchestration
- `prompts.py`: RAG prompt templates

**Generation Flow**:
```
Query + Retrieved Contexts → Build RAG Prompt → LLM Inference → Answer
```

### 7. Vector Store Layer (`app/vectorstore/`)

**Purpose**: Vector embedding storage and similarity search

**Components**:
- `qdrant_client.py`: Qdrant connection management
- `indexing.py`: Upsert and search operations

**Configuration**:
- Collection: `documents`
- Vector dimension: 1024
- Distance metric: Cosine similarity

### 8. Graph Layer (`app/graph/`)

**Purpose**: Knowledge graph operations

**Components**:
- `cypher_queries.py`: Entity search queries
- `graph_algorithms.py`: Graph analytics (stats, top entities, relationship distribution)
- `graph_builder.py`: Graph construction from text
- `neo4j_client.py`: Low-level Neo4j operations

**Graph Schema**:
```
(:Entity {name: string, type: string})
[:RELATIONSHIP_TYPE {type: string}]
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | HTTP API |
| Vector Database | Qdrant | Semantic search |
| Graph Database | Neo4j | Knowledge graph |
| Relational Database | PostgreSQL | Metadata storage |
| Embeddings | Alibaba text-embedding-v4 | 1024-dim vectors |
| LLM | Alibaba qwen3.6-flash | Answer generation |
| PDF Parsing | PyMuPDF | Text extraction |
| Document Source | Google Drive | PDF storage |
| ORM | SQLAlchemy | Database abstraction |

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Neo4j 5+
- Qdrant 1.7+
- Google Cloud service account with Drive API access
- Alibaba Model Studio API key

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd graphrag
```

2. **Create virtual environment**:
```bash
python -m venv ksl_env
source ksl_env/bin/activate  # On Windows: ksl_env\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize databases**:
```bash
# PostgreSQL
createdb graphrag

# Qdrant (if using Docker)
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Neo4j (if using Docker)
docker run -p 7474:7474 -p 7687:7687 neo4j:latest
```

6. **Run database migrations** (if using Alembic):
```bash
alembic upgrade head
```

### Configuration

Edit `.env` with your settings:

```env
# PostgreSQL
POSTGRES_URL=postgresql://user:password@localhost:5432/graphrag
POSTGRES_USER=graphuser
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=graphrag

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=documents
QDRANT_VECTOR_SIZE=1024
QDRANT_DISTANCE=Cosine

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
NEO4J_MAX_CONNECTION_POOL_SIZE=50

# Google Drive
GOOGLE_CREDENTIALS_PATH=credentials/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# Alibaba Model Studio
ALIBABA_API_KEY=your_api_key
ALIBABA_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
ALIBABA_MODEL=qwen3.6-flash
ALIBABA_TEMPERATURE=0.0
```

## Usage

### Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

### API Examples

#### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

#### Ingest Documents
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"folder_id": "your_google_drive_folder_id"}'
```

#### Query Documents
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the East African Community?"}'
```

#### Search Graph
```bash
curl -X POST http://localhost:8000/api/v1/graph/search \
  -H "Content-Type: application/json" \
  -d '{"entity": "Customs Union"}'
```

#### Build Graph from Text
```bash
curl -X POST http://localhost:8000/api/v1/graph/build/text \
  -H "Content-Type: application/json" \
  -d '{"text": "The East African Community is an intergovernmental organization..."}'
```

#### Get Graph Statistics
```bash
curl http://localhost:8000/api/v1/graph/stats
```

### Postman Collection

Import `postman_collection.json` into Postman for a complete API testing suite with example requests.

## Performance Characteristics

Based on production logs:

| Operation | Time | Notes |
|-----------|------|-------|
| PDF Parsing | ~2s | Per document |
| Chunking | <0.01s | 203 chunks |
| Embedding | ~31s | 203 chunks, batch size 10 |
| Vector Indexing | ~2s | Qdrant upsert |
| Graph Building | ~51 min | 203 chunks, 15 parallel workers |
| **Total Ingestion** | **~52 min** | Per document (203 chunks) |

**Bottleneck**: Graph building is the slowest step due to LLM API latency. The system processes all chunks (no limits) for comprehensive knowledge extraction.

## Project Structure

```
graphrag/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Route aggregation
│   │       └── routes/
│   │           ├── health.py      # Health check endpoint
│   │           ├── ingest.py      # Ingestion endpoint
│   │           ├── query.py       # Query endpoint
│   │           └── graph.py       # Graph operations
│   ├── core/
│   │   ├── settings.py            # Configuration
│   │   └── logging.py             # Logging setup
│   ├── db/
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── postgres.py            # PostgreSQL connection
│   │   └── neo4j.py               # Neo4j connection
│   ├── ingestion/
│   │   ├── drive_client.py        # Google Drive API
│   │   └── sync_service.py        # Ingestion orchestrator
│   ├── parser/
│   │   └── pdf_parser.py          # PDF text extraction
│   ├── chunking/
│   │   └── splitter.py            # Text chunking
│   ├── embeddings/
│   │   └── embedder.py            # Vector embeddings
│   ├── extraction/
│   │   └── knowledge_extractor.py # Entity/relation extraction
│   ├── graph/
│   │   ├── cypher_queries.py      # Graph queries
│   │   ├── graph_algorithms.py    # Graph analytics
│   │   ├── graph_builder.py       # Graph construction
│   │   └── neo4j_client.py        # Neo4j operations
│   ├── retrieval/
│   │   └── hybrid_retriever.py    # Hybrid search
│   ├── generation/
│   │   ├── llm_client.py          # LLM API client
│   │   ├── answer_engine.py       # Answer generation
│   │   └── prompts.py             # RAG prompts
│   └── vectorstore/
│       ├── qdrant_client.py       # Qdrant connection
│       └── indexing.py            # Vector operations
├── credentials/                   # Service account keys
├── data/                          # Downloaded PDFs
├── tests/                         # Test files
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
├── postman_collection.json        # API testing collection
└── README.md                      # This file
```

## Design Decisions

### Three-Database Architecture

- **PostgreSQL**: ACID-compliant metadata storage with deduplication
- **Qdrant**: High-performance vector search with 1024-dim embeddings
- **Neo4j**: Native graph database for relationship traversal

Each database is optimized for its specific use case, providing the best performance for each operation type.

### Hybrid Retrieval

Combines semantic similarity (vector) with structural relationships (graph) to provide richer context:
- **Vector search**: Finds semantically similar chunks
- **Graph search**: Finds related entities and their relationships
- **Merged context**: Provides both semantic and structural information to the LLM

### Parallel Graph Building

Uses `ThreadPoolExecutor` with 15 workers to process chunks concurrently, significantly reducing ingestion time for large documents.

### Single-Call Knowledge Extraction

Extracts both entities and relations in one LLM call instead of two, reducing API costs and latency by 50%.

### Alibaba Model Studio Integration

Uses Alibaba's OpenAI-compatible API for both embeddings and LLM, avoiding local model hosting and providing cloud-native scalability.

### Deduplication via Checksums

SHA-256 hashing of document content prevents reprocessing the same document, saving time and API costs.

## Troubleshooting

### Common Issues

**Qdrant timeout on startup**:
- Increase timeout in `qdrant_client.py` (currently 120s)
- Check Qdrant is running: `curl http://localhost:6333/`

**LLM API rate limiting**:
- Reduce `max_workers` in `graph_builder.py` (currently 15)
- Check Alibaba API quota

**Embedding batch size error**:
- Ensure batch size is ≤ 10 (Alibaba API limit)
- Check `embedder.py` configuration

**Graph building is slow**:
- Expected: ~15s per LLM call
- Total time depends on chunk count and network latency
- Consider reducing chunk count or increasing parallelism

## Future Enhancements

- [ ] Reranking layer for improved retrieval quality
- [ ] Hierarchical chunking for better context preservation
- [ ] Streaming responses for long answers
- [ ] Async ingestion for non-blocking document processing
- [ ] Graph visualization endpoint
- [ ] Multi-language support
- [ ] Citation and source attribution
- [ ] Incremental graph updates (add/remove entities)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on the repository.
