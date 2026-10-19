from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    title = Column(String)
    source = Column(String)
    source_id = Column(String, index=True)  # Drive file id or upload checksum
    source_link = Column(String)
    checksum = Column(String, unique=True)
    content = Column(Text)

    # pending -> processing -> completed | failed
    status = Column(String, nullable=False, default="pending")
    error = Column(Text)
    chunk_count = Column(Integer)
    entity_count = Column(Integer)
    relation_count = Column(Integer)
    embedding_model = Column(String)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)  # "drive" | "upload"
    target = Column(String)  # folder id or filename

    # queued -> running -> completed | failed
    status = Column(String, nullable=False, default="queued")
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    results = Column(JSON, default=list)
    error = Column(Text)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
