"""Database access for logs. The only place SQLAlchemy queries live."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.logs.model import LogRecord
from app.modules.logs.schema import LogIn


def insert_batch(session: Session, lines: list[LogIn]) -> int:
    records = [
        LogRecord(service=line.service, ts=line.ts, level=line.level, message=line.message)
        for line in lines
    ]
    session.add_all(records)
    session.commit()
    return len(records)


def query_logs(
    session: Session,
    *,
    service: str | None = None,
    level: str | None = None,
    since: datetime | None = None,
    q: str | None = None,
    limit: int = 200,
) -> list[LogRecord]:
    statement = select(LogRecord).order_by(LogRecord.ts.desc(), LogRecord.id.desc())
    if service:
        statement = statement.where(LogRecord.service == service)
    if level:
        statement = statement.where(LogRecord.level == level.lower())
    if since is not None:
        statement = statement.where(LogRecord.ts >= since)
    if q:
        # ILIKE on Postgres, LIKE on SQLite: one code path for both.
        statement = statement.where(LogRecord.message.ilike(f"%{q}%"))
    statement = statement.limit(limit)
    return list(session.scalars(statement))
