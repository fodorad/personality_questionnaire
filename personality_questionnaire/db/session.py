"""Engine and session management.

The database URL comes from ``PQ_DATABASE_URL``, defaulting to a SQLite file under
the user's home directory so a lab machine needs no server and no configuration.

There are no migrations. The schema has one version, and a research tool that owns
its own database is better served by an explicit export and re-import than by a
migration graph nobody exercises. This is a decision, not an omission: see
``docs/storage.md``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker

from personality_questionnaire.db.models import Base

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.pool import ConnectionPoolEntry

__all__ = [
    "create_engine_from_env",
    "database_url",
    "default_database_path",
    "init_db",
    "session_scope",
]

ENV_DATABASE_URL = "PQ_DATABASE_URL"
"""Environment variable naming the database to use."""

ENV_HOME = "PQ_HOME"
"""Environment variable overriding where the default database lives."""


def default_database_path() -> Path:
    """Return the path of the default SQLite database.

    Returns:
        ``$PQ_HOME/records.db`` when set, else ``~/.personality_questionnaire/records.db``.
    """
    home = os.environ.get(ENV_HOME)
    root = Path(home) if home else Path.home() / ".personality_questionnaire"
    return root / "records.db"


def database_url() -> str:
    """Resolve the database URL to use.

    Returns:
        ``$PQ_DATABASE_URL`` when set, otherwise a SQLite URL for
        :func:`default_database_path`.
    """
    configured = os.environ.get(ENV_DATABASE_URL)
    if configured:
        return configured
    return f"sqlite:///{default_database_path()}"


def _enable_sqlite_foreign_keys(
    dbapi_connection: DBAPIConnection, _record: ConnectionPoolEntry
) -> None:
    """Turn on foreign-key enforcement for a SQLite connection.

    SQLite ignores foreign keys unless asked, per connection, so ``ON DELETE CASCADE``
    would silently do nothing and deleting a session would orphan its responses.

    Args:
        dbapi_connection: The raw connection being opened.
        _record: The pool entry, unused.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine_from_env(url: str | None = None, *, echo: bool = False) -> Engine:
    """Build an engine, creating the SQLite parent directory if needed.

    Args:
        url: Database URL. Defaults to :func:`database_url`.
        echo: Whether to log emitted SQL.

    Returns:
        A configured engine.
    """
    resolved = url or database_url()

    if resolved.startswith("sqlite:///") and not resolved.startswith("sqlite:///:memory:"):
        Path(resolved.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(resolved, echo=echo, future=True)

    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine


def init_db(engine: Engine) -> None:
    """Create any missing tables.

    Idempotent, so it is safe to call on every start.

    Args:
        engine: The engine to create tables on.
    """
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[SASession]:
    """Yield a transactional session, committing on success.

    Args:
        engine: The engine to open a session on.

    Yields:
        An open session.

    Raises:
        Exception: Whatever the body raised, after rolling back.
    """
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
