"""The record schema.

Four tables. A participant has sessions; a session has one response per item and one
score per subscale. Reading a record back means loading a session and its children.

Two decisions shape everything here:

**Responses are rows, not a JSON blob.** One row per item costs nothing at this scale
and makes "what did everyone answer to item 5" a query rather than a decode loop over
every record -- which is exactly what a reliability coefficient needs.

**Scores are stored, not recomputed.** A stored score, next to the scoring version and
the hash of the instrument that produced it, is evidence of what a participant was
actually told. Recomputing on read would silently rewrite history whenever the scorer
changed.

String columns carry explicit lengths. SQLite ignores them; MySQL requires them on
any indexed column, and this is the only place the alternate backend shapes the code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

__all__ = ["Base", "Participant", "Response", "Score", "Session"]

_CODE_LENGTH = 64
"""Maximum length of a participant code."""

_NAME_LENGTH = 255
"""Maximum length of a free-text name or label."""

_KEY_LENGTH = 64
"""Maximum length of an instrument key, tag or subscale name."""


def _now() -> datetime:
    """Return the current UTC time.

    Returns:
        An aware datetime in UTC, so records collected in different time zones remain
        comparable.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for every table in this package."""


class Participant(Base):
    """A person who answers questionnaires.

    Identified by a study-local code rather than a name: this package stores
    human-subject data, and a code keeps a record pseudonymous by default.

    Attributes:
        id: Surrogate primary key.
        code: Study-local identifier, unique within the database.
        label: Optional human-readable note, e.g. a cohort or condition.
        notes: Optional free text.
        created_at: When the participant was first recorded.
        sessions: Every administration given to this participant.
    """

    __tablename__ = "participant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(_CODE_LENGTH), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(_NAME_LENGTH), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list[Session]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        order_by="Session.started_at",
    )

    def __repr__(self) -> str:
        """Return a debugging representation."""
        return f"Participant(code={self.code!r})"


class Session(Base):
    """One administration of one instrument to one participant.

    Attributes:
        id: Surrogate primary key.
        participant_id: The participant who answered.
        questionnaire: Registry key of the instrument administered.
        tag: Free-form administration tag, e.g. ``"pre"`` or ``"post"``. Part of the
            uniqueness constraint, which is what lets a paired instrument record two
            sessions for the same participant.
        experiment: Optional study or condition name.
        started_at: When administration began.
        completed_at: When the last item was answered, or ``None`` if abandoned.
        source: How the record was collected -- ``"cli"``, ``"ui"`` or ``"import"``.
        package_version: Version of this package that scored the session.
        git_sha: Commit the scoring code came from, or ``None`` from an installed
            wheel, which has no repository.
        git_dirty: Whether that checkout had uncommitted changes, in which case the
            record cannot be reproduced from any commit.
        instrument_hash: Hash of the instrument definition as administered, so a
            later wording fix cannot retroactively change what was asked.
        scoring_version: Version of the scoring arithmetic used.
        extra: Any additional study-specific metadata.
        participant: The participant who answered.
        responses: One row per item.
        scores: One row per subscale.
    """

    __tablename__ = "session"
    __table_args__ = (
        UniqueConstraint("participant_id", "questionnaire", "tag", "started_at", name="uq_session"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participant.id", ondelete="CASCADE"), index=True
    )
    questionnaire: Mapped[str] = mapped_column(String(_KEY_LENGTH), index=True)
    tag: Mapped[str] = mapped_column(String(_KEY_LENGTH), default="")
    experiment: Mapped[str | None] = mapped_column(String(_NAME_LENGTH), default=None, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    source: Mapped[str] = mapped_column(String(16), default="cli")

    package_version: Mapped[str] = mapped_column(String(32), default="")
    git_sha: Mapped[str | None] = mapped_column(String(40), default=None)
    git_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    instrument_hash: Mapped[str] = mapped_column(String(80), default="")
    scoring_version: Mapped[int] = mapped_column(Integer, default=1)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    participant: Mapped[Participant] = relationship(back_populates="sessions")
    responses: Mapped[list[Response]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Response.item_number",
    )
    scores: Mapped[list[Score]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return a debugging representation."""
        return f"Session(questionnaire={self.questionnaire!r}, tag={self.tag!r})"


class Response(Base):
    """One item answered in one session.

    Attributes:
        id: Surrogate primary key.
        session_id: The session this answer belongs to.
        item_number: The item's number in its instrument's own numbering.
        value: The response as given, before any reverse-keying.
        responded_at: When the item was answered, when the collector records it.
        session: The owning session.
    """

    __tablename__ = "response"
    __table_args__ = (UniqueConstraint("session_id", "item_number", name="uq_response"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("session.id", ondelete="CASCADE"), index=True
    )
    item_number: Mapped[int] = mapped_column(Integer)
    value: Mapped[int] = mapped_column(Integer)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    session: Mapped[Session] = relationship(back_populates="responses")

    def __repr__(self) -> str:
        """Return a debugging representation."""
        return f"Response(item={self.item_number}, value={self.value})"


class Score(Base):
    """One computed subscale value for one session.

    Attributes:
        id: Surrogate primary key.
        session_id: The session scored.
        subscale: Name of the subscale.
        level: The subscale's level, e.g. ``"domain"`` or ``"facet"``.
        value: The computed score.
        normalized: Whether the value is rescaled to ``[0, 1]``. Part of the
            uniqueness constraint, so a normalised score and a published total can
            coexist for the same subscale.
        session: The owning session.
    """

    __tablename__ = "score"
    __table_args__ = (UniqueConstraint("session_id", "subscale", "normalized", name="uq_score"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("session.id", ondelete="CASCADE"), index=True
    )
    subscale: Mapped[str] = mapped_column(String(_KEY_LENGTH))
    level: Mapped[str] = mapped_column(String(_KEY_LENGTH), default="subscale")
    value: Mapped[float] = mapped_column(Float)
    normalized: Mapped[bool] = mapped_column(Boolean, default=True)

    session: Mapped[Session] = relationship(back_populates="scores")

    def __repr__(self) -> str:
        """Return a debugging representation."""
        return f"Score(subscale={self.subscale!r}, value={self.value})"
