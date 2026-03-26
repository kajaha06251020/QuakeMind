"""Add research journal, hypotheses, experiment logs tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_journal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_journal_created_at", "research_journal", ["created_at"])
    op.create_index("ix_journal_entry_type", "research_journal", ["entry_type"])

    op.create_table(
        "hypotheses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("trigger_event", sa.String(), nullable=True),
        sa.Column("verify_after_days", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hypotheses_status", "hypotheses", ["status"])
    op.create_index("ix_hypotheses_created_at", "hypotheses", ["created_at"])

    op.create_table(
        "experiment_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("experiment_name", sa.String(), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=True),
        sa.Column("results_json", sa.JSON(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experiments_created_at", "experiment_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("experiment_logs")
    op.drop_table("hypotheses")
    op.drop_table("research_journal")
