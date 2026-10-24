"""The logs table.

Indexes on (service, ts) and level match the query patterns:
filtering by service and time range, and by level, is the hot path.
Text search uses ILIKE (Postgres) / LIKE (SQLite) in the repository;
on Postgres this can be upgraded to a tsvector column with a GIN
index without changing the API.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LogRecord(Base):
    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_logs_service_ts", "service", "ts"),
        Index("ix_logs_level", "level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service: Mapped[str] = mapped_column(String(200), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
