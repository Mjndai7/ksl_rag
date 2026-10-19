import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes import ingest as ingest_routes
from app.api.v1.routes import query as query_routes
from app.generation.answer_engine import cited_source_numbers
from app.main import app

# No `with TestClient(...)`: the lifespan (which connects to Qdrant/Neo4j) is not run.
client = TestClient(app)


def test_health():
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_query_returns_answer_and_numbered_sources(monkeypatch):
    def fake_run_query(query, with_answer=True):
        return {
            "answer": "Sunday is excluded [1].",
            "cited_sources": [1],
            "warnings": [],
            "vector_hits": [{}],
            "graph_hits": [],
            "merged_contexts": [{
                "text": "57. In computing time...",
                "source": "vector",
                "score": 0.8,
                "metadata": {"document_name": "Cap. 2.pdf", "section_label": "s. 57", "source_link": "http://x"},
            }],
        }

    monkeypatch.setattr(query_routes, "run_query", fake_run_query)
    body = client.post("/api/v1/query", json={"query": "How is time computed?"}).json()

    assert body["answer"] == "Sunday is excluded [1]."
    assert body["sources"][0] == {
        "n": 1, "type": "vector", "score": 0.8, "document": "Cap. 2.pdf",
        "section": "s. 57", "link": "http://x", "text": "57. In computing time...",
    }
    assert body["retrieval"] == {"vector_hits": 1, "graph_hits": 0}


def test_query_validates_input():
    assert client.post("/api/v1/query", json={"query": ""}).status_code == 422


def test_upload_rejects_non_pdf():
    r = client.post("/api/v1/ingest/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_upload_rejects_fake_pdf():
    r = client.post("/api/v1/ingest/upload", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400


def test_upload_queues_background_job(monkeypatch, tmp_path):
    jobs = []
    monkeypatch.setattr(ingest_routes.settings, "DOWNLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(ingest_routes.repository, "create_job", lambda source, target: {"id": "job-1", "status": "queued"})

    class FakeService:
        def run_job(self, job_id, **kw):
            jobs.append((job_id, kw))

    monkeypatch.setattr(ingest_routes, "IngestionSyncService", FakeService)
    r = client.post("/api/v1/ingest/upload", files={"file": ("../evil.pdf", b"%PDF-1.4 ...", "application/pdf")})

    assert r.status_code == 202
    assert r.json()["status_url"] == "/api/v1/ingest/jobs/job-1"
    job_id, kw = jobs[0]
    assert kw["pdf_path"].startswith(str(tmp_path / "uploads"))
    assert kw["pdf_path"].endswith("_evil.pdf")  # path traversal stripped


@pytest.mark.parametrize("answer,n,expected", [
    ("See [1] and [3][3].", 3, [1, 3]),
    ("Out of range [7].", 3, []),
    ("No citations.", 3, []),
])
def test_cited_source_numbers(answer, n, expected):
    assert cited_source_numbers(answer, n) == expected
