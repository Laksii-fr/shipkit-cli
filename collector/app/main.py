"""ShipKit collector entry point.

create_app() is a factory so tests can inject a SQLite database URL.
The module-level `app` is what uvicorn serves.
"""

from fastapi import FastAPI

from app.core.config import Settings
from app.core.database import Database
from app.modules.health.route import router as health_router
from app.modules.logs.route import router as logs_router


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.db = Database(database_url or settings.database_url)
    app.include_router(logs_router)
    app.include_router(health_router)
    return app


app = create_app()
