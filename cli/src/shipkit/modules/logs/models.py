"""Data models for the logs feature (CLI side)."""

from datetime import datetime

from pydantic import BaseModel


class LogLine(BaseModel):
    """One log line, as shipped to and returned from the collector."""

    service: str
    ts: datetime
    level: str
    message: str


class LogRecord(LogLine):
    """A stored log line, with its collector id."""

    id: int | None = None
