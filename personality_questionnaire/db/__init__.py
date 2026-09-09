"""Persistent storage for collected records.

A *record* is one administration of one instrument to one participant: a
:class:`~personality_questionnaire.db.models.Session` row with its responses, its
computed scores, and the provenance needed to reproduce those scores later.

Storage is SQLAlchemy over SQLite by default, so a lab machine needs no server. Point
``PQ_DATABASE_URL`` at MySQL when several machines share one database.
"""

from __future__ import annotations

from personality_questionnaire.db.models import (
    Base,
    Participant,
    Response,
    Score,
    Session,
)
from personality_questionnaire.db.repository import Record, RecordSummary, Repository
from personality_questionnaire.db.session import (
    create_engine_from_env,
    database_url,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "Participant",
    "Record",
    "RecordSummary",
    "Repository",
    "Response",
    "Score",
    "Session",
    "create_engine_from_env",
    "database_url",
    "init_db",
    "session_scope",
]
