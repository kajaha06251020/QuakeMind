"""SQLAlchemy テーブルモデル定義。"""
import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EarthquakeEventDB(Base):
    __tablename__ = "earthquake_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_events_occurred_at", "occurred_at"),
        Index("ix_events_region", "region"),
        Index("ix_events_magnitude", "magnitude"),
    )


class AlertDB(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("earthquake_events.event_id"), unique=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String, nullable=False)
    ja_text: Mapped[str] = mapped_column(Text, nullable=False)
    en_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    route_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_severity", "severity"),
    )


class SeenEventDB(Base):
    __tablename__ = "seen_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserSettingsDB(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    min_severity: Mapped[str] = mapped_column(String, default="LOW")
    region_filters: Mapped[list] = mapped_column(JSON, default=list)
    notification_channels: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
