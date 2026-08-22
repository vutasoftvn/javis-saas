from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from agentos.api.db.models import Base

DEFAULT_DB_PATH = Path("var/agentos/chat.sqlite3")


def get_database_url() -> str:
    db_url = os.getenv("AGENTOS_DB_URL") or os.getenv("DATABASE_URL")
    if db_url:
        # Normalize postgres:// to postgresql:// if needed for SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH.resolve()}"


_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, echo=False)
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory


def get_db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


from sqlalchemy.pool import StaticPool


def reset_db_for_testing(engine_url: str = "sqlite:///:memory:"):
    global _engine, _SessionFactory
    connect_args = {"check_same_thread": False} if engine_url.startswith("sqlite") else {}
    poolclass = StaticPool if engine_url == "sqlite:///:memory:" else None
    
    kwargs = {"connect_args": connect_args}
    if poolclass:
        kwargs["poolclass"] = poolclass
        
    _engine = create_engine(engine_url, **kwargs)
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine
