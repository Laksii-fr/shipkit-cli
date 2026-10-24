"""Pydantic schemas for the logs API.

Timestamps are normalised to naive UTC on the way in: SQLite does
not preserve tzinfo, and mixing aware/naive values breaks the
`since` comparison. Postgres deployments store the same naive UTC.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value


class LogIn(BaseModel):
    service: str
    ts: datetime
    level: str
    message: str

    @field_validator("level")
    @classmethod
    def _normalise_level(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("ts")
    @classmethod
    def _normalise_ts(cls, value: datetime) -> datetime:
        return _naive_utc(value)


class IngestBatch(BaseModel):
    lines: list[LogIn]


class IngestResult(BaseModel):
    accepted: int


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service: str
    ts: datetime
    level: str
    message: str
