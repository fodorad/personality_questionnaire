"""Application state.

Two layers, kept apart on purpose:

* :class:`AppState` is process-wide -- the record store and the cached listing that
  every browser connection shares.
* :class:`DraftRecord` is per-connection: one participant part-way through one
  questionnaire. Two browser tabs are two independent drafts.

All the logic the interface needs lives here rather than in ``pages/``: progress,
completeness, which items remain. That is what lets the page modules stay thin
element-building code, and it is why they are excluded from coverage while this
module is tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from personality_questionnaire import registry
from personality_questionnaire.core.config import settings

if TYPE_CHECKING:
    from personality_questionnaire.db import Record, RecordSummary, Repository
    from personality_questionnaire.registry import Questionnaire
    from personality_questionnaire.scoring import ScoreResult

__all__ = ["AppState", "DraftRecord", "state"]


@dataclass(slots=True)
class DraftRecord:
    """One questionnaire in progress, owned by a single browser connection.

    Attributes:
        participant_code: Study-local identifier for the person answering.
        participant_label: Optional note, e.g. a cohort.
        experiment: Optional study or condition name.
        tag: Administration tag, e.g. ``"pre"``.
        questionnaire_key: Registry key of the chosen instrument.
        responses: Item number to response value, filled in as the participant goes.
        started_at: When the first item was answered.
        notes: Free text the operator can attach.
        read_only: Whether this draft was loaded from storage for viewing rather
            than answering. A freshly-started draft is never read-only.
        loaded_session_id: The database id this draft was loaded from, if any. A
            later save updates that session in place instead of inserting a new
            one.
    """

    participant_code: str = ""
    participant_label: str = ""
    experiment: str = ""
    tag: str = ""
    questionnaire_key: str | None = None
    responses: dict[int, int] = field(default_factory=dict)
    started_at: datetime | None = None
    notes: str = ""
    read_only: bool = False
    loaded_session_id: int | None = None

    @property
    def instrument(self) -> Questionnaire | None:
        """The chosen instrument, or ``None`` if none has been chosen."""
        if self.questionnaire_key is None:
            return None
        return registry.get(self.questionnaire_key)

    @property
    def ready(self) -> bool:
        """Whether setup is complete enough to begin answering."""
        return bool(self.participant_code.strip()) and self.questionnaire_key is not None

    @property
    def n_items(self) -> int:
        """How many items the chosen instrument has, or zero if none is chosen."""
        instrument = self.instrument
        return instrument.n_items if instrument else 0

    @property
    def answered(self) -> int:
        """How many items have been answered."""
        return len(self.responses)

    @property
    def missing(self) -> tuple[int, ...]:
        """Item numbers still unanswered, in order."""
        return tuple(n for n in range(1, self.n_items + 1) if n not in self.responses)

    @property
    def complete(self) -> bool:
        """Whether every item has been answered."""
        return self.n_items > 0 and not self.missing

    @property
    def progress(self) -> float:
        """Fraction of items answered, from 0.0 to 1.0."""
        if self.n_items == 0:
            return 0.0
        return self.answered / self.n_items

    def answer(self, number: int, value: int) -> None:
        """Record one response.

        Args:
            number: The item's number.
            value: The response given.

        Raises:
            ValueError: If the draft is read-only, no instrument is chosen, the
                item does not exist, or the value falls outside the instrument's
                response range.
        """
        if self.read_only:
            raise ValueError("this record is read-only; call unlock() to edit it")

        instrument = self.instrument
        if instrument is None:
            raise ValueError("choose an instrument before answering")

        if number not in instrument.item_numbers:
            raise ValueError(f"{instrument.key} has no item {number}")

        if not instrument.minimum <= value <= instrument.maximum:
            raise ValueError(
                f"{instrument.key} responses must lie in "
                f"[{instrument.minimum}..{instrument.maximum}], got {value}"
            )

        if self.started_at is None:
            self.started_at = datetime.now(UTC)
        self.responses[number] = value

    def score(self) -> ScoreResult:
        """Score the draft as it stands.

        Returns:
            The computed scores.

        Raises:
            ValueError: If the draft is incomplete.
        """
        from personality_questionnaire import scoring

        instrument = self.instrument
        if instrument is None or not self.complete:
            raise ValueError("the questionnaire is not finished")

        answers = [self.responses[n] for n in range(1, instrument.n_items + 1)]
        return scoring.score(instrument, [answers])

    def to_record(self) -> Record:
        """Convert the draft into a storable record.

        Returns:
            The record.

        Raises:
            ValueError: If the draft is incomplete.
        """
        from personality_questionnaire.db import Record

        if not self.complete:
            raise ValueError("the questionnaire is not finished")

        return Record(
            participant_code=self.participant_code.strip(),
            questionnaire=self.questionnaire_key or "",
            responses=dict(self.responses),
            tag=self.tag.strip(),
            experiment=self.experiment.strip() or None,
            participant_label=self.participant_label.strip() or None,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            source="ui",
            extra={"notes": self.notes} if self.notes.strip() else {},
        )

    def clear_responses(self) -> None:
        """Discard every answer, keeping the participant and instrument."""
        self.responses.clear()
        self.started_at = None

    def reset(self) -> None:
        """Return the draft to its initial state, ready for a new participant."""
        self.participant_code = ""
        self.participant_label = ""
        self.experiment = ""
        self.tag = ""
        self.questionnaire_key = None
        self.notes = ""
        self.read_only = False
        self.loaded_session_id = None
        self.clear_responses()

    def load_from(self, record: Record, *, read_only: bool = True) -> None:
        """Populate every field from a stored record, for viewing or editing.

        Replaces the draft's participant identity, instrument, responses, tag,
        experiment and notes with the record's own, and remembers
        ``record.session_id`` so a later save updates that session instead of
        inserting a new one.

        Args:
            record: The stored record to load.
            read_only: Whether the draft should render inert until explicitly
                unlocked. Defaults to True: a loaded record is always viewed
                before it can be edited.

        Raises:
            ValueError: If ``record.session_id`` is ``None`` -- an unsaved record
                cannot be "loaded back".
        """
        if record.session_id is None:
            raise ValueError("cannot load a record that has not been saved")

        self.participant_code = record.participant_code
        self.participant_label = record.participant_label or ""
        self.experiment = record.experiment or ""
        self.tag = record.tag
        self.questionnaire_key = record.questionnaire
        self.responses = dict(record.responses)
        self.started_at = record.started_at
        self.notes = record.extra.get("notes", "") if record.extra else ""
        self.read_only = read_only
        self.loaded_session_id = record.session_id

    def unlock(self) -> None:
        """Allow a loaded draft to be edited.

        Identity fields (participant, instrument, tag) are not re-exposed by this
        alone -- the questionnaire tab is the only place an unlocked draft is
        edited, and it never shows those fields -- this just clears the flag that
        keeps answers from being changed.
        """
        self.read_only = False


@dataclass(slots=True)
class AppState:
    """Process-wide services shared by every connection.

    Attributes:
        database_url: The record store in use, or ``None`` for the package default.
    """

    database_url: str | None = None
    _repository: Repository | None = field(default=None, repr=False)
    _records: list[RecordSummary] | None = field(default=None, repr=False)

    @property
    def repository(self) -> Repository:
        """The record store, opened on first use."""
        if self._repository is None:
            from personality_questionnaire.db import Repository, create_engine_from_env

            url = self.database_url or settings.database_url
            self._repository = Repository(create_engine_from_env(url))
        return self._repository

    def records(self) -> list[RecordSummary]:
        """Return every stored record, newest first.

        Read fresh every time rather than cached. The database is shared -- the CLI
        writes to it, and a second machine may too -- so a cached listing goes stale
        the moment anything outside this process saves a record, and showing an
        operator "no records yet" when the database holds several is worse than the
        cost of a query against a table this size.

        Returns:
            The stored records.
        """
        return self.repository.list()

    def invalidate(self) -> None:
        """Retained for callers that signal a write; listings are already uncached."""
        self._records = None

    def save(self, record: Record) -> Record:
        """Store a record and refresh the listing.

        Args:
            record: The record to store.

        Returns:
            The saved record, carrying its new id.
        """
        saved = self.repository.save(record)
        self.invalidate()
        return saved

    def update(self, session_id: int, record: Record) -> Record:
        """Update a stored record in place and refresh the listing.

        Args:
            session_id: The existing session to overwrite.
            record: The new responses and metadata.

        Returns:
            The updated record.
        """
        updated = self.repository.update(session_id, record)
        self.invalidate()
        return updated

    def set_database(self, url: str) -> None:
        """Switch to a different record store, closing the previous one.

        The new database is opened eagerly (not left to the next lazy access) so a
        bad path or a permission error surfaces here, in the setup handler that
        triggered the switch, rather than on some unrelated later call.

        Args:
            url: The new database URL, e.g. ``sqlite:///path/to/file.db``.
        """
        from personality_questionnaire.core import recent_databases

        self.close()
        self.database_url = url
        _ = self.repository  # open + init_db now, so failures surface immediately
        recent_databases.remember_database(url)

    def delete(self, session_id: int) -> bool:
        """Delete a record and refresh the listing.

        Args:
            session_id: The record's id.

        Returns:
            True if a record was deleted.
        """
        deleted = self.repository.delete(session_id)
        self.invalidate()
        return deleted

    def close(self) -> None:
        """Release the record store."""
        if self._repository is not None:
            self._repository.close()
            self._repository = None
        self.invalidate()


state = AppState()
"""The single shared application state."""
