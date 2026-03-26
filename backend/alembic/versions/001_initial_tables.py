"""Initial tables: earthquake_events, alerts, seen_events, user_settings.

Revision ID: 001
Revises:
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "earthquake_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.String(), unique=True, nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=False),
        sa.Column("depth_km", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_occurred_at", "earthquake_events", ["occurred_at"])
    op.create_index("ix_events_region", "earthquake_events", ["region"])
    op.create_index("ix_events_magnitude", "earthquake_events", ["magnitude"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.String(), sa.ForeignKey("earthquake_events.event_id"), unique=True, nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("ja_text", sa.Text(), nullable=False),
        sa.Column("en_text", sa.Text(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), default=False),
        sa.Column("risk_json", sa.JSON(), nullable=True),
        sa.Column("route_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])

    op.create_table(
        "seen_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(), unique=True, nullable=False),
        sa.Column("min_severity", sa.String(), default="LOW"),
        sa.Column("region_filters", sa.JSON(), default=list),
        sa.Column("notification_channels", sa.JSON(), default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_table("seen_events")
    op.drop_table("alerts")
    op.drop_table("earthquake_events")
