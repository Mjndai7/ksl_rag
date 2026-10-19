"""document ingestion status and ingestion jobs

Revision ID: 20261019_0002
Revises: 20260514_0001
Create Date: 2026-10-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261019_0002"
down_revision: Union[str, Sequence[str], None] = "20260514_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_id", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("source_link", sa.String(), nullable=True))
    # Rows from before this migration predate status tracking; mark them legacy so they
    # are re-ingested with the current embedding model instead of being skipped.
    op.add_column(
        "documents",
        sa.Column("status", sa.String(), nullable=False, server_default="legacy"),
    )
    op.alter_column("documents", "status", server_default=None)
    op.add_column("documents", sa.Column("error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("entity_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("relation_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("embedding_model", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_documents_source_id", "documents", ["source_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=True),
        sa.Column("processed_files", sa.Integer(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_documents_source_id", table_name="documents")
    for col in (
        "updated_at", "created_at", "embedding_model", "relation_count", "entity_count",
        "chunk_count", "error", "status", "source_link", "source_id",
    ):
        op.drop_column("documents", col)
