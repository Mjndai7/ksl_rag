# KSL GraphRAG — Hybrid Retrieval over the Laws of Kenya

A FastAPI service that ingests statute PDFs (from Google Drive or upload), indexes them in
**Qdrant** (vectors) and **Neo4j** (knowledge graph), tracks them in **Postgres**, and answers
questions with cited, section-level sources. Both pipelines are orchestrated with **LangGraph**,
and all model calls go through **OpenRouter** (free models by default).

## Architecture

```
                    FastAPI  (/api/v1)
   ┌───────────────┬────────────────┬──────────────┬──────────────┐
   │ /ingest       │ /query         │ /graph/*     │ /documents   │
   │ /ingest/upload│ /retrieve      │              │              │
   └──────┬────────┴───────┬────────┴──────┬───────┴──────┬───────┘
          │ background job │               │              │
          ▼                ▼               │              │
  LangGraph ingestion   LangGraph retrieval│              │
  parse                  ┌ vector_retrieve ┐              │
  check_duplicate ──skip─┤                 ├ merge        │
  register               └ graph_retrieve ─┘   │          │
  chunk                                     generate      │
  embed ─────────────── OpenRouter (embeddings + chat) ───┘
  index ──────────────▶ Qdrant   (chunks + section metadata)
  build_graph ────────▶ Neo4j    (Entity/Document graph with provenance)
  finalize ───────────▶ Postgres (documents, ingestion_jobs)
  (any failure → fail: document marked failed with the error)
```

### Ingestion (`app/workflows/ingestion_graph.py`)

| Step | What it does |
|---|---|
| `parse` | PyMuPDF text extraction, then `clean_text` strips Laws of Kenya page headers, ligatures and NBSPs; SHA-256 of the text |
| `check_duplicate` | Skips a document already `completed` with the current embedding model; otherwise reuses its id so a re-ingest *replaces* old vectors and graph facts |
| `register` | Upserts the Postgres `documents` row with `status=processing` |
| `chunk` | Section-aware chunking: splits on statute sections (`57. In computing time…`), packs small sections, splits long ones on word boundaries with overlap. Each chunk carries its section numbers and headings |
| `embed` | Batched OpenRouter embeddings, prefixed with the Act title and section. Fails loudly, never stores placeholder vectors |
| `index` | Deterministic Qdrant point ids (`uuid5(document_id:chunk_index)`); old points for the document are deleted first |
| `build_graph` | Packs chunks into ~24k-char batches (**one LLM call per batch**, keeping within free-tier limits), extracts legal entities and relations, writes them with batched `UNWIND` queries. Failed batches are retried as two halves |
| `finalize` | Marks the document `completed` with chunk, entity and relation counts |

Jobs run in the background; poll `GET /api/v1/ingest/jobs/{job_id}`.

### Knowledge graph model (Neo4j)

- `(:Entity {key, name, type, description, doc_ids})`. `key` is a normalised name with a uniqueness constraint, so "The Commission." and "commission" merge.
- `(:Document {id, title})`, with `(:Entity)-[:MENTIONED_IN]->(:Document)`.
- `(:Entity)-[:ESTABLISHES|DEFINES|AMENDS|… {evidence, doc_ids}]->(:Entity)`. `evidence` records `document|title|section|chunk`, so every fact is citable and removable per document.
- The full-text index `entity_name_ft` on name and description powers graph retrieval from natural-language questions.

### Retrieval and answering (`app/workflows/retrieval_graph.py`)

Vector search (top-k chunks) and graph search (full-text keyword match on entities, then their relations) run **in parallel**. Results are merged (statute text first, then graph facts) and sent to the LLM with numbered sources. The answer cites `[n]`, and the API returns those sources with document, section and Drive link. If Neo4j is down, answers still come from vectors and a warning is returned.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/health/ready` | Checks Postgres, Neo4j, Qdrant, OpenRouter key (503 if any fail) |
| POST | `/api/v1/ingest` | `{folder_id?, extract_graph?, force?, limit?}` → 202 + `job_id` (Google Drive) |
| POST | `/api/v1/ingest/upload` | multipart `file` (PDF), `extract_graph?`, `force?` → 202 + `job_id` |
| GET | `/api/v1/ingest/jobs/{job_id}` | Job status with per-file results and step timings |
| POST | `/api/v1/query` | `{query}` → answer, `cited_sources`, numbered `sources` |
| POST | `/api/v1/retrieve` | `{query}` → retrieval only (no LLM call, no quota) |
| GET | `/api/v1/documents` | Ingested documents and their status |
| GET/DELETE | `/api/v1/documents/{id}` | Inspect, or delete a document's vectors, graph facts and row |
| POST | `/api/v1/graph/search` | `{entity, limit?}` → matching relations and entities |
| GET | `/api/v1/graph/entity/{name}` | Entity neighbourhood |
| GET | `/api/v1/graph/stats` | Counts, top entities, relation types |
| POST | `/api/v1/graph/build/text` | `{text, title?, document_id?}` → extract into the graph |
| POST | `/api/v1/graph/build/chunks` | `{chunks, document_id, title?}` |

Interactive docs: `http://localhost:8000/docs`.

## Models (OpenRouter)

| Setting | Default |
|---|---|
| `LLM_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free` |
| `LLM_FALLBACK_MODELS` | `google/gemma-4-31b-it:free,nvidia/nemotron-3.5-lightning:free` (tried in order on errors or rate limits) |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `nvidia/nemotron-3-embed-1b:free` / `2048` |

**Free-tier budget:** a free OpenRouter key allows **50 free-model chat requests per day**. Embeddings don't count against it. Each `/query` uses 1 request. Ingestion uses about 1 request per 24k characters of statute (Cap. 3 ≈ 2, all six sample Caps ≈ 27). Use `extract_graph=false` to ingest vectors only, and `/retrieve` to test retrieval without spending quota. Changing the embedding model means changing its dimension: use a new `QDRANT_COLLECTION`, because startup refuses to use a collection with the wrong vector size.

## Running locally (no Docker)

```bash
python -m venv ksl_env && source ksl_env/bin/activate
pip install -r requirements-dev.txt
cp .env.docker.example .env      # then point hosts at localhost and fill in secrets

# Services: Postgres (Postgres.app / brew), ./qdrant binary, neo4j-community/bin/neo4j console
alembic upgrade head
uvicorn app.main:app --reload
```

Tests:

```bash
pytest                          # unit tests: no services or API key needed
python scripts/smoke_test.py    # live end-to-end check of every endpoint against a running server
python scripts/smoke_test.py --skip-llm --skip-drive   # no OpenRouter chat quota, no Drive
```

## Docker / Railway

`docker compose up -d` runs Postgres, Neo4j, Qdrant and the app using `.env.docker` (copy it from `.env.docker.example`). The container entrypoint writes `GOOGLE_CREDENTIALS_JSON` to `GOOGLE_CREDENTIALS_PATH`, runs `alembic upgrade head`, and serves on `$PORT` (default 8000). See `DEPLOYMENT.md`.

## Project layout

```
app/
  api/v1/routes/      health, ingest, query, documents, graph
  core/               settings, OpenRouter client
  db/                 Postgres engine, models, repository; Neo4j driver and schema
  parser/             PDF text extraction, cleaning
  chunking/           section-aware statute chunker
  embeddings/         OpenRouter embeddings
  vectorstore/        Qdrant collection and indexing
  extraction/         batched LLM entity/relation extraction
  graph/              graph builder, queries, stats, name normalisation
  retrieval/          hybrid retriever, context merging
  generation/         LLM client, prompts, cited answers
  workflows/          LangGraph ingestion and retrieval graphs, entry points
  ingestion/          Google Drive client, job runner
alembic/              migrations (documents, ingestion_jobs)
scripts/smoke_test.py live endpoint test
tests/                unit tests
```
