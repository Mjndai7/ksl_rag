"""Postgres access for documents and ingestion jobs."""
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Document, IngestionJob
from app.db.postgres import session_scope


def _as_dict(row) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name != "content"}


# ---- documents -------------------------------------------------------------

def find_document(checksum: str, source_id: Optional[str]) -> Optional[dict]:
    """Document matching this content, or else the same source file (an updated version)."""
    with session_scope() as db:
        doc = db.query(Document).filter(Document.checksum == checksum).first()
        if doc is None and source_id:
            doc = (
                db.query(Document)
                .filter(Document.source_id == source_id)
                .order_by(Document.created_at.desc().nullslast())
                .first()
            )
        return _as_dict(doc) if doc else None


def upsert_document_processing(
    document_id: Optional[str],
    *,
    title: str,
    source: str,
    source_id: Optional[str],
    source_link: Optional[str],
    checksum: str,
    content: str,
    embedding_model: str,
) -> str:
    with session_scope() as db:
        doc = db.get(Document, document_id) if document_id else None
        if doc is None:
            doc = Document()
            db.add(doc)
        doc.title = title
        doc.source = source
        doc.source_id = source_id
        doc.source_link = source_link
        doc.checksum = checksum
        doc.content = content
        doc.embedding_model = embedding_model
        doc.status = "processing"
        doc.error = None
        db.flush()
        return doc.id


def update_document(document_id: str, **fields) -> None:
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        for k, v in fields.items():
            setattr(doc, k, v)


def list_documents() -> list[dict]:
    with session_scope() as db:
        rows = db.query(Document).order_by(Document.created_at.desc().nullslast()).all()
        return [_as_dict(r) for r in rows]


def get_document(document_id: str) -> Optional[dict]:
    with session_scope() as db:
        doc = db.query(Document).filter(or_(Document.id == document_id, Document.source_id == document_id)).first()
        return _as_dict(doc) if doc else None


def delete_document_row(document_id: str) -> None:
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is not None:
            db.delete(doc)


# ---- ingestion jobs --------------------------------------------------------

def create_job(source: str, target: Optional[str]) -> dict:
    with session_scope() as db:
        job = IngestionJob(source=source, target=target, status="queued", results=[], total_files=0, processed_files=0)
        db.add(job)
        db.flush()
        return _as_dict(job)


def update_job(job_id: str, **fields) -> None:
    with session_scope() as db:
        job = db.get(IngestionJob, job_id)
        if job is None:
            return
        for k, v in fields.items():
            setattr(job, k, v)


def append_job_result(job_id: str, result: dict) -> None:
    with session_scope() as db:
        job = db.get(IngestionJob, job_id)
        if job is None:
            return
        job.results = [*(job.results or []), result]
        job.processed_files = (job.processed_files or 0) + 1
        flag_modified(job, "results")


def get_job(job_id: str) -> Optional[dict]:
    with session_scope() as db:
        job = db.get(IngestionJob, job_id)
        return _as_dict(job) if job else None
