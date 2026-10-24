"""Logs routes. Thin: parse input, call the controller, return."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.logs import controller
from app.modules.logs.schema import IngestBatch, IngestResult, LogOut

router = APIRouter(tags=["logs"])


def _session(request: Request) -> Session:
    return request.app.state.db.session()


@router.post("/ingest", status_code=202, response_model=IngestResult)
def ingest(request: Request, batch: IngestBatch) -> IngestResult:
    session = _session(request)
    try:
        accepted = controller.ingest(session, batch)
    finally:
        session.close()
    return IngestResult(accepted=accepted)


@router.get("/logs", response_model=list[LogOut])
def logs(
    request: Request,
    service: str | None = None,
    level: str | None = None,
    since: str | None = None,
    q: str | None = None,
    limit: int = 200,
) -> list[LogOut]:
    session = _session(request)
    try:
        return controller.search(
            session, service=service, level=level, since=since, q=q, limit=limit
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    finally:
        session.close()
