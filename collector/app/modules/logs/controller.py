"""Logs business logic: ingest and search, with `since` parsing.

Routes stay thin: they hand the controller a session and plain
values, and it does the work.
"""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.modules.logs import repository
from app.modules.logs.schema import IngestBatch, LogOut

_SINCE_PATTERN = re.compile(r"^(?P<amount>\d+)(?P<unit>[mhd])$")
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def parse_since(since: str | None, *, now: datetime | None = None) -> datetime | None:
    """'30m', '1h', '2d' -> the cutoff datetime (naive UTC)."""
    if since is None:
        return None
    match = _SINCE_PATTERN.match(since.strip())
    if not match:
        raise ValueError(
            f"Invalid since value '{since}'. Use e.g. 30m, 1h or 2d."
        )
    seconds = int(match.group("amount")) * _UNIT_SECONDS[match.group("unit")]
    return (now or _utcnow()) - timedelta(seconds=seconds)


def ingest(session: Session, batch: IngestBatch) -> int:
    return repository.insert_batch(session, batch.lines)


def search(
    session: Session,
    *,
    service: str | None = None,
    level: str | None = None,
    since: str | None = None,
    q: str | None = None,
    limit: int = 200,
) -> list[LogOut]:
    cutoff = parse_since(since)
    records = repository.query_logs(
        session, service=service, level=level, since=cutoff, q=q, limit=limit
    )
    return [LogOut.model_validate(record) for record in records]
