"""Engine, session factory, and the as-of context that prevents leakage."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from datetime import date
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    """Lazily built engine so importing the package never opens a connection.

    Settings are read on each construction rather than captured at import.
    Binding them at import time silently pins the process to whatever
    configuration existed when the module was first touched, which breaks
    runtime reconfiguration and makes test isolation depend on import order.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        kwargs: dict = {"echo": settings.sql_echo, "future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=10)
        _engine = create_engine(url, **kwargs)

        if url.startswith("sqlite"):
            # SQLite ignores foreign keys unless asked; the tests rely on the
            # cascade behaviour that production PostgreSQL enforces.
            @event.listens_for(_engine, "connect")
            def _fk_on(dbapi_conn, _record):  # pragma: no cover - trivial
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope. Commits on success, rolls back on failure."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db(drop: bool = False) -> None:
    engine = get_engine()
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def reset_engine() -> None:
    """Drop cached engine/session state. Used by tests to switch databases."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()


# --------------------------------------------------------------------------
# As-of context: the structural defence against hindsight leakage
# --------------------------------------------------------------------------
_as_of: contextvars.ContextVar[date | None] = contextvars.ContextVar("as_of", default=None)


@contextmanager
def as_of(when: date | None) -> Iterator[None]:
    """Restrict every as-of-aware query to facts published on or before ``when``.

    Placing this in the data-access layer rather than in agent prompts is what
    makes historical mode trustworthy: an agent cannot see future information
    even if its prompt invites it to, because the rows never reach it.

    >>> with as_of(date(2015, 1, 1)):
    ...     ...  # queries filtered through apply_as_of see only pre-2015 facts
    """
    token = _as_of.set(when)
    try:
        yield
    finally:
        _as_of.reset(token)


def current_as_of() -> date | None:
    return _as_of.get()


def apply_as_of(query, column):
    """Apply the active as-of filter to ``query`` on ``column``.

    Rows whose date is NULL are excluded while a cutoff is active: an undated
    fact cannot be shown to predate the cutoff, and assuming it does is exactly
    the leak this mechanism exists to prevent.
    """
    cutoff = current_as_of()
    if cutoff is None:
        return query
    return query.filter(column.isnot(None), column <= cutoff)
