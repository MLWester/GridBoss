from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/gridboss"

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine(database_url: str | None = None) -> Engine:
    """Create (or reuse) the SQLAlchemy engine."""
    global _engine  # noqa: PLW0603 - cache engine for reuse

    if _engine is None:
        url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        _engine = create_engine(url, future=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Return the configured sessionmaker instance."""
    global SessionLocal  # noqa: PLW0603 - cache sessionmaker

    if SessionLocal is None:
        engine = get_engine()
        SessionLocal = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return SessionLocal


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency-friendly session generator."""
    session_factory = get_sessionmaker()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
