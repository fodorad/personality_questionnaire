"""Turning stored records into files.

Three shapes, because three different readers want different things:

* **JSON** -- one record, self-describing, including its provenance. The archival
  form: enough to reconstruct exactly what was administered and what was reported.
* **Wide CSV** -- one row per session, columns for every item and every subscale.
  What a statistics package expects for a single instrument.
* **Long CSV** -- one row per value. The tidy form, and the only one that can hold
  several instruments in a single file without inventing empty columns.
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

from personality_questionnaire import registry
from personality_questionnaire.db.models import Participant, Response, Score, Session
from personality_questionnaire.db.session import session_scope

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from personality_questionnaire.db.repository import Repository

__all__ = ["SHAPES", "record_to_json", "to_csv", "to_json"]

SHAPES = ("wide", "long", "json")
"""Export shapes the CLI and the application offer."""


def record_to_json(repository: Repository, session_id: int) -> dict[str, Any]:
    """Build the archival JSON form of one record.

    Args:
        repository: The repository holding the record.
        session_id: The record's session id.

    Returns:
        A self-describing mapping: participant, session, provenance, responses and
        the scores as they were stored.

    Raises:
        KeyError: If no record carries that id.
    """
    from personality_questionnaire.db.repository import SCHEMA_VERSION

    record = repository.load(session_id)

    with session_scope(repository.engine) as session:
        row = session.get(Session, session_id)
        if row is None:
            raise KeyError(f"no record with id {session_id}")
        provenance = {
            "package_version": row.package_version,
            "git_sha": row.git_sha,
            "git_dirty": row.git_dirty,
            "instrument_hash": row.instrument_hash,
            "scoring_version": row.scoring_version,
        }
        scores: dict[str, dict[str, float]] = {}
        for score in session.query(Score).filter(Score.session_id == session_id):
            scores.setdefault(score.level, {})[score.subscale] = score.value

    return {
        "schema_version": SCHEMA_VERSION,
        "participant": {
            "code": record.participant_code,
            "label": record.participant_label,
        },
        "session": {
            "questionnaire": record.questionnaire,
            "tag": record.tag,
            "experiment": record.experiment,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "source": record.source,
            "extra": record.extra,
        },
        "provenance": provenance,
        "responses": {str(k): v for k, v in sorted(record.responses.items())},
        "scores": scores,
    }


def to_json(repository: Repository, session_ids: list[int]) -> list[dict[str, Any]]:
    """Build the archival JSON form of several records.

    Args:
        repository: The repository holding them.
        session_ids: Which records to export.

    Returns:
        One mapping per record, in the order given.
    """
    return [record_to_json(repository, session_id) for session_id in session_ids]


def _rows(engine: Engine, session_ids: list[int]) -> list[tuple[Session, str, dict, dict]]:
    """Load the sessions to export together with their responses and scores.

    Args:
        engine: The database to read from.
        session_ids: Which sessions to load.

    Returns:
        One tuple per session: the row, the participant code, item responses and
        stored scores.
    """
    out = []
    with session_scope(engine) as session:
        for session_id in session_ids:
            row = session.get(Session, session_id)
            if row is None:
                continue
            participant = session.get(Participant, row.participant_id)
            code = participant.code if participant else "unknown"
            responses = {
                r.item_number: r.value
                for r in session.query(Response).filter(Response.session_id == session_id)
            }
            scores = {
                s.subscale: s.value
                for s in session.query(Score).filter(Score.session_id == session_id)
            }
            out.append((row, code, responses, scores))
    return out


def _wide(engine: Engine, session_ids: list[int]) -> str:
    """Render one row per session, with item and subscale columns.

    Every exported session must use the same instrument: a wide file with mixed
    instruments would need a union of every item column, mostly empty.

    Args:
        engine: The database to read from.
        session_ids: Which sessions to export.

    Returns:
        CSV text.

    Raises:
        ValueError: If the selected records span more than one instrument.
    """
    loaded = _rows(engine, session_ids)
    if not loaded:
        return ""

    instruments = {row.questionnaire for row, _, _, _ in loaded}
    if len(instruments) > 1:
        raise ValueError(
            "the wide shape holds one instrument at a time, but the selection spans "
            f"{sorted(instruments)}; use --shape long instead"
        )

    instrument = registry.get(next(iter(instruments)))
    item_columns = [f"item_{n}" for n in range(1, instrument.n_items + 1)]
    score_columns = [s.name for s in instrument.subscales]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "participant_code",
            "questionnaire",
            "tag",
            "experiment",
            "started_at",
            "package_version",
            "git_sha",
            *item_columns,
            *score_columns,
        ]
    )
    for row, code, responses, scores in loaded:
        writer.writerow(
            [
                code,
                row.questionnaire,
                row.tag,
                row.experiment or "",
                row.started_at.isoformat() if row.started_at else "",
                row.package_version,
                row.git_sha or "",
                *[responses.get(n, "") for n in range(1, instrument.n_items + 1)],
                *[scores.get(name, "") for name in score_columns],
            ]
        )
    return buffer.getvalue()


def _long(engine: Engine, session_ids: list[int]) -> str:
    """Render one row per value, across any mix of instruments.

    Args:
        engine: The database to read from.
        session_ids: Which sessions to export.

    Returns:
        CSV text.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["participant_code", "session_id", "questionnaire", "tag", "kind", "key", "value"]
    )
    for row, code, responses, scores in _rows(engine, session_ids):
        for number, value in sorted(responses.items()):
            writer.writerow([code, row.id, row.questionnaire, row.tag, "response", number, value])
        for name, value in sorted(scores.items()):
            writer.writerow([code, row.id, row.questionnaire, row.tag, "score", name, value])
    return buffer.getvalue()


def to_csv(engine: Engine, session_ids: list[int], *, shape: str = "wide") -> str:
    """Render records as CSV in the requested shape.

    Args:
        engine: The database to read from.
        session_ids: Which sessions to export.
        shape: ``"wide"`` or ``"long"``.

    Returns:
        CSV text.

    Raises:
        ValueError: If the shape is unknown, or a wide export spans instruments.
    """
    if shape == "wide":
        return _wide(engine, session_ids)
    if shape == "long":
        return _long(engine, session_ids)
    raise ValueError(f"unknown shape {shape!r}; use one of {', '.join(SHAPES)}")
