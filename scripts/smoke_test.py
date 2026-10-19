"""End-to-end smoke test of every API endpoint against a running server.

    python scripts/smoke_test.py [--base http://localhost:8000] [--pdf "data/raw/Cap. 3 - ....pdf"]
                                 [--skip-drive] [--skip-llm]

Uses real services: OpenRouter quota is consumed by graph extraction and /query
(--skip-llm avoids both). Exits non-zero if any check fails.
"""
import argparse
import sys
import time
from pathlib import Path

import httpx

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{' — ' + detail if detail else ''}", flush=True)
    return ok


def wait_job(c, job_id, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = c.get(f"/api/v1/ingest/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(5)
    return c.get(f"/api/v1/ingest/jobs/{job_id}").json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--pdf", default="data/raw/Cap. 3 - Kenya Law Reform Commission Act.pdf")
    p.add_argument("--question", default="What are the functions of the Kenya Law Reform Commission?")
    p.add_argument("--skip-drive", action="store_true")
    p.add_argument("--skip-llm", action="store_true", help="no graph extraction and no /query")
    p.add_argument("--timeout", type=int, default=1800)
    args = p.parse_args()

    c = httpx.Client(base_url=args.base, timeout=600)

    r = c.get("/api/v1/health")
    check("GET /health", r.status_code == 200 and r.json()["status"] == "ok")

    r = c.get("/api/v1/health/ready")
    check("GET /health/ready", r.status_code == 200, str(r.json()["checks"]))

    # --- ingest an uploaded PDF through the LangGraph ingestion workflow
    pdf = Path(args.pdf)
    with pdf.open("rb") as fh:
        r = c.post(
            "/api/v1/ingest/upload",
            files={"file": (pdf.name, fh, "application/pdf")},
            data={"extract_graph": str(not args.skip_llm).lower(), "force": "true"},
        )
    check("POST /ingest/upload -> 202", r.status_code == 202, r.text[:200])
    job = wait_job(c, r.json()["job_id"], args.timeout)
    result = (job.get("results") or [{}])[0]
    check(
        "upload job completed",
        job["status"] == "completed" and result.get("status") == "completed",
        f"chunks={result.get('chunks')} graph={result.get('graph')} timings={result.get('timings')} error={result.get('error') or job.get('error')}",
    )
    document_id = result.get("document_id")

    with pdf.open("rb") as fh:
        r = c.post("/api/v1/ingest/upload", files={"file": (pdf.name, fh, "application/pdf")})
    job = wait_job(c, r.json()["job_id"], 300)
    check("re-upload is skipped as duplicate", (job.get("results") or [{}])[0].get("status") == "skipped")

    r = c.get("/api/v1/documents")
    docs = r.json()["documents"]
    check("GET /documents", r.status_code == 200 and any(d["id"] == document_id for d in docs), f"{len(docs)} documents")

    r = c.get(f"/api/v1/documents/{document_id}")
    check("GET /documents/{id}", r.status_code == 200 and r.json()["status"] == "completed",
          f"chunk_count={r.json().get('chunk_count')} entities={r.json().get('entity_count')}")
    check("GET /documents/{missing} -> 404", c.get("/api/v1/documents/nope").status_code == 404)

    # --- retrieval
    r = c.post("/api/v1/retrieve", json={"query": args.question})
    body = r.json()
    check("POST /retrieve", r.status_code == 200 and len(body["vector_hits"]) > 0,
          f"vector={len(body['vector_hits'])} graph={len(body['graph_hits'])} top={body['sources'][0]['document'] if body['sources'] else None} {body['sources'][0]['section'] if body['sources'] else ''}")
    if not args.skip_llm:
        check("graph retrieval finds facts for a natural-language question", len(body["graph_hits"]) > 0,
              "; ".join(h["text"] for h in body["graph_hits"][:3]))

        r = c.post("/api/v1/query", json={"query": args.question})
        body = r.json()
        check("POST /query", r.status_code == 200 and bool(body.get("answer")),
              f"cited={body.get('cited_sources')} warnings={body.get('warnings')}")
        print("\n--- answer ---\n" + str(body.get("answer")) + "\n--------------\n")
        check("answer cites sources", len(body.get("cited_sources") or []) > 0)

    # --- graph endpoints
    r = c.get("/api/v1/graph/stats")
    stats = r.json()
    check("GET /graph/stats", r.status_code == 200, str(stats.get("stats")))
    top = (stats.get("top_entities") or [{}])[0].get("entity")

    r = c.post("/api/v1/graph/search", json={"entity": "Commission"})
    check("POST /graph/search", r.status_code == 200, f"{len(r.json()['results'])} relations, {len(r.json()['entities'])} entities")

    if top:
        r = c.get(f"/api/v1/graph/entity/{top}")
        check("GET /graph/entity/{name}", r.status_code == 200 and len(r.json()["neighborhood"]) > 0, f"{top}: {len(r.json()['neighborhood'])} neighbours")

    if not args.skip_llm:
        text = ("The Kenya Law Reform Commission Act establishes the Kenya Law Reform Commission. "
                "The Commission reports to the Attorney-General and reviews the laws of Kenya.")
        r = c.post("/api/v1/graph/build/text", json={"text": text, "title": "smoke-test", "document_id": "smoke-test"})
        check("POST /graph/build/text", r.status_code == 200 and r.json()["graph_results"]["failed_batches"] == 0, str(r.json().get("graph_results")))

        r = c.post("/api/v1/graph/build/chunks", json={"chunks": [text], "document_id": "smoke-test", "title": "smoke-test"})
        check("POST /graph/build/chunks (idempotent re-build)", r.status_code == 200, str(r.json().get("graph_results")))

    # --- Google Drive ingestion
    if not args.skip_drive:
        r = c.post("/api/v1/ingest", json={"limit": 1, "extract_graph": False})
        if check("POST /ingest (Drive) -> 202", r.status_code == 202, r.text[:200]):
            job = wait_job(c, r.json()["job_id"], args.timeout)
            check("Drive job completed", job["status"] == "completed",
                  f"{[(x.get('title'), x.get('status'), x.get('error')) for x in job.get('results') or []]} {job.get('error') or ''}")

    print(f"\n{sum(ok for _, ok in RESULTS)}/{len(RESULTS)} checks passed")
    return 0 if all(ok for _, ok in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
