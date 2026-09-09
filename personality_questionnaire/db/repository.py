"""Reading and writing records.

:class:`Repository` is the only thing the CLI and the application talk to. Callers
pass and receive plain :class:`Record` values rather than ORM instances, so nothing
outside this package holds a detached session or depends on SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from personality_questionnaire import registry, scoring
from personality_questionnaire.db.models import Participant, Response, Score, Session
from personality_questionnaire.db.session import init_db, session_scope
from personality_questionnaire.provenance import capture, instrument_hash

if TYPE_CHECKING:
    import builtins

    from sqlalchemy import Engine

__all__ = ["Record", "RecordSummary", "Repository"]

SCHEMA_VERSION = 1
"""Version of the exported record format."""


@dataclass(frozen=True, slots=True)
class Record:
    """One complete administration, independent of the database.

    Attributes:
        participant_code: The participant's study-local code.
        questionnaire: Registry key of the instrument.
        responses: Item number to response value.
        tag: Administration tag, e.g. ``"pre"``.
        experiment: Optional study or condition name.
        participant_label: Optional label for the participant.
        started_at: When administration began.
        completed_at: When it finished.
        source: How it was collected.
        extra: Study-specific metadata.
        session_id: Database id, set once the record has been saved.
    """

    participant_code: str
    questionnaire: str
    responses: dict[int, int]
    tag: str = ""
    experiment: str | None = None
    participant_label: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source: str = "cli"
    extra: dict[str, Any] = field(default_factory=dict)
    session_id: int | None = None

    @property
    def instrument(self) -> registry.Questionnaire:
        """The instrument this record was collected with."""
        return registry.get(self.questionnaire)

    @property
    def answers(self) -> list[int]:
        """Responses in item order.

        Returns:
            One value per item, ordered by item number.

        Raises:
            ValueError: If any item is unanswered, since a partial record cannot be
                scored.
        """
        expected = self.instrument.n_items
        missing = [n for n in range(1, expected + 1) if n not in self.responses]
        if missing:
            raise ValueError(
                f"{self.questionnaire} record for {self.participant_code} is missing "
                f"items {missing}"
            )
        return [self.responses[n] for n in range(1, expected + 1)]

    def score(self) -> scoring.ScoreResult:
        """Score this record.

        Returns:
            The computed scores for the single participant.
        """
        return scoring.score(self.instrument, [self.answers])


@dataclass(frozen=True, slots=True)
class RecordSummary:
    """A record's metadata without its responses, for listings.

    Attributes:
        session_id: Database id.
        participant_code: The participant's code.
        questionnaire: Registry key of the instrument.
        tag: Administration tag.
        experiment: Study or condition name.
        started_at: When administration began.
        completed_at: When it finished, if it did.
        n_responses: How many items were answered.
        source: How the record was collected.
    """

    session_id: int
    participant_code: str
    questionnaire: str
    tag: str
    experiment: str | None
    started_at: datetime | None
    completed_at: datetime | None
    n_responses: int
    source: str

    @property
    def complete(self) -> bool:
        """Whether every item of the instrument was answered."""
        return self.n_responses == registry.get(self.questionnaire).n_items


class Repository:
    """Stores and retrieves records.

    Attributes:
        engine: The engine every operation runs against.
    """

    def __init__(self, engine: Engine, *, create: bool = True) -> None:
        """Bind to an engine.

        Args:
            engine: The database to use.
            create: Whether to create missing tables on construction.
        """
        self.engine = engine
        if create:
            init_db(engine)

    def close(self) -> None:
        """Release every pooled connection.

        A long-lived process opens one repository and never closes it, but a test or
        a short-lived command should hand its connections back rather than leaving
        the pool to be finalised at interpreter exit.
        """
        self.engine.dispose()

    def __enter__(self) -> Repository:
        """Enter a context that closes the repository on exit.

        Returns:
            This repository.
        """
        return self

    def __exit__(self, *_exc: object) -> None:
        """Close the repository."""
        self.close()

    def save(self, record: Record) -> Record:
        """Persist a record together with its scores and provenance.

        Scores are computed once, here, and stored. They are never recomputed on
        read: a stored score is evidence of what a participant was told, and the
        scoring version and instrument hash beside it say how it was produced.

        Args:
            record: The record to save. Must be complete.

        Returns:
            The same record with :attr:`Record.session_id` populated.

        Raises:
            ValueError: If the record is missing responses, or its instrument is not
                registered.
        """
        instrument = record.instrument
        result = record.score()
        provenance = capture()

        with session_scope(self.engine) as session:
            participant = session.scalar(
                select(Participant).where(Participant.code == record.participant_code)
            )
            if participant is None:
                participant = Participant(
                    code=record.participant_code, label=record.participant_label
                )
                session.add(participant)
                session.flush()
            elif record.participant_label and not participant.label:
                participant.label = record.participant_label

            row = Session(
                participant_id=participant.id,
                questionnaire=record.questionnaire,
                tag=record.tag,
                experiment=record.experiment,
                started_at=record.started_at or provenance.captured_at,
                completed_at=record.completed_at or provenance.captured_at,
                source=record.source,
                package_version=provenance.package_version,
                git_sha=provenance.git_sha,
                git_dirty=provenance.git_dirty,
                instrument_hash=instrument_hash(instrument),
                scoring_version=scoring.SCORING_VERSION,
                extra=dict(record.extra),
            )
            session.add(row)
            session.flush()

            session.add_all(
                Response(session_id=row.id, item_number=number, value=value)
                for number, value in sorted(record.responses.items())
            )
            session.add_all(
                Score(
                    session_id=row.id,
                    subscale=subscale.name,
                    level=subscale.level,
                    value=float(result.values[0, index]),
                    normalized=result.normalized
                    and subscale.aggregation is not registry.Aggregation.SUM,
                )
                for index, subscale in enumerate(instrument.subscales)
            )
            session.flush()
            session_id = row.id

        return replace(record, session_id=session_id)

    def update(self, session_id: int, record: Record) -> Record:
        """Overwrite an existing session's responses and scores in place.

        The session's identity -- ``participant_code``, ``questionnaire`` and
        ``tag`` -- is locked to what the row already has; the same three fields on
        ``record`` are ignored, because changing them would make this a different
        administration rather than an edit of this one, and they participate in
        the table's uniqueness constraint.

        Provenance (``package_version``, ``git_sha``, ``git_dirty``,
        ``instrument_hash``, ``scoring_version``) and ``completed_at`` are
        re-captured from the *current* environment rather than preserved from the
        original save: an edit is a new act of recording, and what is stored
        should be evidence of what actually happened, not a patch that silently
        keeps stale metadata from before. This mirrors the "scores are stored, not
        recomputed" rule the schema already follows -- see ``docs/storage.md``.

        Args:
            session_id: The session to overwrite.
            record: The new responses and metadata. Its ``participant_code``,
                ``questionnaire`` and ``tag`` are ignored.

        Returns:
            The updated record, reflecting what was actually stored -- including
            the locked identity fields, which come from the existing row rather
            than from ``record``.

        Raises:
            KeyError: If no session carries that id.
            ValueError: If ``record`` is missing responses for the instrument.
        """
        with session_scope(self.engine) as session:
            row = session.get(Session, session_id)
            if row is None:
                raise KeyError(f"no record with id {session_id}")

            instrument = registry.get(row.questionnaire)
            missing = [n for n in range(1, instrument.n_items + 1) if n not in record.responses]
            if missing:
                raise ValueError(
                    f"{instrument.key} record for session {session_id} is missing items {missing}"
                )
            answers = [record.responses[n] for n in range(1, instrument.n_items + 1)]

            result = scoring.score(instrument, [answers])
            provenance = capture()

            if record.participant_label and not row.participant.label:
                row.participant.label = record.participant_label
            row.experiment = record.experiment
            row.source = record.source
            row.completed_at = provenance.captured_at
            row.package_version = provenance.package_version
            row.git_sha = provenance.git_sha
            row.git_dirty = provenance.git_dirty
            row.instrument_hash = instrument_hash(instrument)
            row.scoring_version = scoring.SCORING_VERSION
            row.extra = dict(record.extra)

            session.execute(sql_delete(Response).where(Response.session_id == session_id))
            session.execute(sql_delete(Score).where(Score.session_id == session_id))
            session.add_all(
                Response(session_id=session_id, item_number=number, value=value)
                for number, value in sorted(record.responses.items())
            )
            session.add_all(
                Score(
                    session_id=session_id,
                    subscale=subscale.name,
                    level=subscale.level,
                    value=float(result.values[0, index]),
                    normalized=result.normalized
                    and subscale.aggregation is not registry.Aggregation.SUM,
                )
                for index, subscale in enumerate(instrument.subscales)
            )
            session.flush()

            questionnaire = row.questionnaire
            participant_code = row.participant.code
            tag = row.tag

        return replace(
            record,
            session_id=session_id,
            questionnaire=questionnaire,
            participant_code=participant_code,
            tag=tag,
        )

    def load(self, session_id: int) -> Record:
        """Load one record by its database id.

        Args:
            session_id: The session's id.

        Returns:
            The record.

        Raises:
            KeyError: If no session carries that id.
        """
        with session_scope(self.engine) as session:
            row = session.scalar(
                select(Session)
                .where(Session.id == session_id)
                .options(selectinload(Session.responses), selectinload(Session.participant))
            )
            if row is None:
                raise KeyError(f"no record with id {session_id}")
            return _to_record(row)

    def list(
        self,
        *,
        participant: str | None = None,
        questionnaire: str | None = None,
        experiment: str | None = None,
    ) -> builtins.list[RecordSummary]:
        """List stored records, most recent first.

        Args:
            participant: Restrict to one participant code.
            questionnaire: Restrict to one instrument.
            experiment: Restrict to one experiment name.

        Returns:
            Matching record summaries.
        """
        counts = (
            select(Response.session_id, func.count(Response.id).label("n"))
            .group_by(Response.session_id)
            .subquery()
        )
        query = (
            select(Session, Participant.code, func.coalesce(counts.c.n, 0))
            .join(Participant, Participant.id == Session.participant_id)
            .outerjoin(counts, counts.c.session_id == Session.id)
            .order_by(Session.started_at.desc(), Session.id.desc())
        )
        if participant is not None:
            query = query.where(Participant.code == participant)
        if questionnaire is not None:
            query = query.where(Session.questionnaire == questionnaire)
        if experiment is not None:
            query = query.where(Session.experiment == experiment)

        with session_scope(self.engine) as session:
            return [
                RecordSummary(
                    session_id=row.id,
                    participant_code=code,
                    questionnaire=row.questionnaire,
                    tag=row.tag,
                    experiment=row.experiment,
                    started_at=_as_utc(row.started_at),
                    completed_at=_as_utc(row.completed_at),
                    n_responses=n,
                    source=row.source,
                )
                for row, code, n in session.execute(query).all()
            ]

    def delete(self, session_id: int) -> bool:
        """Delete one record and everything belonging to it.

        Args:
            session_id: The session's id.

        Returns:
            True if a record was deleted.
        """
        with session_scope(self.engine) as session:
            row = session.get(Session, session_id)
            if row is None:
                return False
            # Deleting through the ORM rather than a bulk DELETE so the configured
            # cascades run on every backend, not only where the database enforces
            # them -- and so the return value needs no dialect-specific rowcount.
            session.delete(row)
            return True

    def participants(self) -> builtins.list[str]:
        """List every participant code, sorted.

        Returns:
            The codes.
        """
        with session_scope(self.engine) as session:
            return sorted(session.scalars(select(Participant.code)).all())

    def scores(self, session_id: int) -> dict[str, float]:
        """Return the stored scores for a record.

        These are the values computed when the record was saved, not a fresh
        computation, so they remain valid evidence even after the scorer changes.

        Args:
            session_id: The session's id.

        Returns:
            Subscale name to stored value.
        """
        with session_scope(self.engine) as session:
            rows = session.scalars(select(Score).where(Score.session_id == session_id)).all()
            return {row.subscale: row.value for row in rows}

    def responses_for(
        self, questionnaire: str
    ) -> tuple[builtins.list[str], builtins.list[builtins.list[int]]]:
        """Return every complete response set for one instrument.

        The shape analysis needs: one row per session, one column per item, plus the
        participant code for each row.

        Args:
            questionnaire: Registry key of the instrument.

        Returns:
            Participant codes and their responses, aligned.
        """
        instrument = registry.get(questionnaire)
        codes: list[str] = []
        answers: list[list[int]] = []

        with session_scope(self.engine) as session:
            rows = session.scalars(
                select(Session)
                .where(Session.questionnaire == questionnaire)
                .options(selectinload(Session.responses), selectinload(Session.participant))
                .order_by(Session.started_at, Session.id)
            ).all()
            for row in rows:
                values = {r.item_number: r.value for r in row.responses}
                if len(values) != instrument.n_items:
                    continue
                codes.append(row.participant.code)
                answers.append([values[n] for n in range(1, instrument.n_items + 1)])

        return codes, answers


def _as_utc(moment: datetime | None) -> datetime | None:
    """Re-attach UTC to a timestamp read back from the database.

    Everything is written as an aware UTC datetime, but SQLite has no timezone type
    and returns naive values. The instant is correct; only the offset is missing.
    Restoring it here keeps a loaded record comparable with a freshly built one,
    which a naive/aware comparison would otherwise refuse outright.

    Args:
        moment: The timestamp as read, or ``None``.

    Returns:
        The same instant, marked UTC.
    """
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=UTC)


def _to_record(row: Session) -> Record:
    """Convert a loaded session row into a plain record.

    Args:
        row: The session, with responses and participant loaded.

    Returns:
        The equivalent record.
    """
    return Record(
        participant_code=row.participant.code,
        questionnaire=row.questionnaire,
        responses={r.item_number: r.value for r in row.responses},
        tag=row.tag,
        experiment=row.experiment,
        participant_label=row.participant.label,
        started_at=_as_utc(row.started_at),
        completed_at=_as_utc(row.completed_at),
        source=row.source,
        extra=dict(row.extra or {}),
        session_id=row.id,
    )
