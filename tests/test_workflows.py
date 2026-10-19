import pytest

from app.workflows import ingestion_graph as ig
from app.workflows.retrieval_graph import build_retrieval_graph


class FakeRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.updates = []

    def find_document(self, checksum, source_id):
        return self.existing

    def upsert_document_processing(self, document_id, **fields):
        self.registered = fields
        return document_id or "doc-1"

    def update_document(self, document_id, **fields):
        self.updates.append((document_id, fields))


@pytest.fixture
def pipeline(monkeypatch):
    repo = FakeRepo()
    calls = {}
    monkeypatch.setattr(ig, "repository", repo)
    monkeypatch.setattr(ig, "parse_pdf", lambda path: "Short title.\n1. This Act may be cited as the Test Act.")
    monkeypatch.setattr(ig, "embed_chunks", lambda texts: [[0.1, 0.2] for _ in texts])
    monkeypatch.setattr(ig, "upsert_chunks", lambda **kw: calls.setdefault("upsert", kw))

    class FakeGraphBuilder:
        def build_graph_for_document(self, **kw):
            calls["graph"] = kw
            return {"entities": 3, "relations": 2, "batches": 1, "failed_batches": 0}

    monkeypatch.setattr(ig, "graph_builder", FakeGraphBuilder())
    graph = ig.build_ingestion_graph()
    return graph, repo, calls


def _run(graph, **extra):
    state = {"pdf_path": "x.pdf", "title": "Cap. 9 - Test Act.pdf", "source": "upload", **extra}
    return ig.summarize(graph.invoke(state))


def test_ingestion_runs_every_step(pipeline):
    graph, repo, calls = pipeline
    result = _run(graph)

    assert result["status"] == "completed", result
    assert result["document_id"] == "doc-1"
    assert result["chunks"] == 1
    assert set(result["timings"]) == {
        "parse", "check_duplicate", "register", "chunk", "embed", "index", "build_graph", "finalize",
    }
    assert calls["upsert"]["metadata"]["document_id"] == "doc-1"
    assert calls["graph"]["title"] == "Cap. 9 - Test Act.pdf"
    assert repo.updates[-1][1]["status"] == "completed"
    assert repo.updates[-1][1]["entity_count"] == 3


def test_up_to_date_duplicate_is_skipped(pipeline, monkeypatch):
    graph, repo, calls = pipeline
    from app.core.settings import settings

    repo.existing = {"id": "doc-0", "checksum": None, "status": "completed", "embedding_model": settings.EMBEDDING_MODEL}
    # Make the stored checksum match whatever parse() computes.
    monkeypatch.setattr(repo, "find_document", lambda checksum, sid: {**repo.existing, "checksum": checksum})

    result = _run(graph)
    assert result["status"] == "skipped"
    assert "upsert" not in calls

    forced = _run(graph, force=True)
    assert forced["status"] == "completed"
    assert forced["document_id"] == "doc-0"  # re-ingested under the same id


def test_failure_marks_document_failed(pipeline, monkeypatch):
    graph, repo, calls = pipeline

    def boom(texts):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(ig, "embed_chunks", boom)
    result = _run(graph)

    assert result["status"] == "failed"
    assert result["failed_step"] == "embed"
    assert "rate limited" in result["error"]
    assert repo.updates[-1] == ("doc-1", {"status": "failed", "error": result["error"]})
    assert "graph" not in calls


def test_graph_extraction_can_be_disabled(pipeline):
    graph, repo, calls = pipeline
    result = _run(graph, extract_graph=False)
    assert result["status"] == "completed"
    assert result["graph"] == {"skipped": True}
    assert "graph" not in calls


class FakeRetriever:
    def __init__(self, graph_error=None):
        self.graph_error = graph_error

    def vector_retrieve(self, q):
        return [{"text": "s. 57 computation of time", "source": "vector", "metadata": {}}]

    def graph_retrieve(self, q):
        if self.graph_error:
            raise self.graph_error
        return [{"text": "Act defines excluded day", "source": "graph", "metadata": {}}]


class FakeAnswerEngine:
    def answer(self, question, contexts):
        return {"answer": f"{len(contexts)} sources [1]", "cited_sources": [1]}


def test_retrieval_graph_merges_parallel_branches_and_answers():
    graph = build_retrieval_graph(FakeRetriever(), FakeAnswerEngine())
    out = graph.invoke({"query": "time", "warnings": []})
    assert [c["source"] for c in out["merged_contexts"]] == ["vector", "graph"]
    assert out["answer"] == "2 sources [1]"
    assert out["warnings"] == []


def test_retrieval_graph_survives_graph_failure():
    graph = build_retrieval_graph(FakeRetriever(graph_error=ConnectionError("neo4j down")), FakeAnswerEngine())
    out = graph.invoke({"query": "time", "warnings": []})
    assert out["answer"] == "1 sources [1]"
    assert "neo4j down" in out["warnings"][0]


def test_retrieval_graph_can_skip_generation():
    graph = build_retrieval_graph(FakeRetriever(), FakeAnswerEngine())
    out = graph.invoke({"query": "time", "with_answer": False, "warnings": []})
    assert "answer" not in out
