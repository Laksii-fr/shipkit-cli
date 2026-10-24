"""Health check: service up, and can it reach the database?"""

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    db_status = "ok"
    try:
        session = request.app.state.db.session()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()
    except Exception:  # noqa: BLE001 - health must report, never raise
        db_status = "unreachable"
    return {"status": "ok" if db_status == "ok" else "degraded", "database": db_status}
