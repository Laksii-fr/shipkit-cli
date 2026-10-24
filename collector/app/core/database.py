"""Database engine/session factory.

One Database object is created by the app factory and stored on
app.state. Nothing here is a module-level mutable global, so tests
can build their own Database on SQLite.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, url: str) -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=connect_args)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Session:
        return self._session_factory()

    def create_all(self) -> None:
        from app.modules.logs.model import Base

        Base.metadata.create_all(self.engine)
