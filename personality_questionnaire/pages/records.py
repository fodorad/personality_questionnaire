"""The records tab: browse what has been collected, and export it."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire import registry
from personality_questionnaire.core import theme
from personality_questionnaire.core.state import state
from personality_questionnaire.db import export as export_module
from personality_questionnaire.pages.components import card_style, notify_detached

if TYPE_CHECKING:
    from collections.abc import Callable

    from personality_questionnaire.core.state import DraftRecord

__all__ = ["render"]

_ALL = "all"
"""Filter value meaning no restriction."""


def render(
    draft: DraftRecord, navigate: Callable[[str], None], on_change: Callable[[], None]
) -> None:
    """Build the records tab.

    Args:
        draft: The connection's draft, reset when starting a new record.
        navigate: Switches to another tab by name.
        on_change: Called after a change that affects other tabs.
    """
    from nicegui import context

    client = context.client
    chosen = {"instrument": _ALL}

    with ui.column().classes("w-full items-center gap-3").style("padding-top:0.5rem"):
        with ui.row().classes("w-full items-center gap-2 no-wrap").style("max-width:52rem"):
            instrument_filter = (
                ui.select(
                    {_ALL: "All instruments", **{k: k for k in registry.keys()}},
                    value=_ALL,
                    label="Instrument",
                )
                .props("dense outlined")
                .classes("w-56")
            )

            ui.space()

            ui.button(
                "New record",
                icon="add",
                on_click=lambda: _start_new(draft, navigate, on_change),
            ).props("unelevated").style(f"background:{theme.PRIMARY}")

        table = ui.column().classes("w-full gap-2").style("max-width:52rem")

        with ui.row().classes("w-full gap-2 justify-end").style("max-width:52rem"):
            ui.label("Export").classes("text-sm self-center").style(f"color:{theme.NEUTRAL}")
            for shape, label in (("wide", "Wide CSV"), ("long", "Long CSV"), ("json", "JSON")):
                ui.button(
                    label,
                    icon="download",
                    on_click=lambda s=shape: _export(client, chosen["instrument"], s),
                ).props("flat")

    def redraw() -> None:
        """Rebuild the listing under the current filter."""
        table.clear()
        summaries = state.records()
        if chosen["instrument"] != _ALL:
            summaries = [s for s in summaries if s.questionnaire == chosen["instrument"]]

        with table:
            if not summaries:
                ui.label("No records yet.").classes("text-sm").style(f"color:{theme.NEUTRAL}")
                return
            for summary in summaries:
                _row(client, draft, navigate, summary, redraw, on_change)

    def filter_changed(event) -> None:  # noqa: ANN001 - NiceGUI event argument
        """Apply the instrument filter."""
        chosen["instrument"] = event.value
        redraw()

    instrument_filter.on_value_change(filter_changed)
    redraw()


def _row(
    client,  # noqa: ANN001
    draft: DraftRecord,
    navigate: Callable[[str], None],
    summary,  # noqa: ANN001
    redraw: Callable[[], None],
    on_change: Callable[[], None],
) -> None:
    """Render one stored record.

    Clicking it loads it read-only; the delete button stops that click from also
    opening the record it just deleted.

    Args:
        client: The connection, for detached toasts.
        draft: The connection's draft, replaced with the loaded record on click.
        navigate: Switches to another tab by name -- used to jump to Questionnaire
            once a record is loaded.
        summary: The record to show.
        redraw: Rebuilds the listing after a deletion.
        on_change: Called after a change that affects other tabs.
    """
    card = ui.card().classes("w-full cursor-pointer").style(card_style())
    card.on("click", lambda: _open(client, draft, navigate, on_change, summary.session_id))

    with card, ui.row().classes("w-full items-center gap-3 no-wrap"):
        ui.label(f"#{summary.session_id}").classes("text-xs font-mono").style(
            f"color:{theme.NEUTRAL};min-width:3rem"
        )
        with ui.column().classes("gap-0 flex-grow min-w-0"):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.label(summary.participant_code).classes("font-medium")
                ui.badge(summary.questionnaire, color=theme.PRIMARY)
                if summary.tag:
                    ui.badge(summary.tag, color=theme.NEUTRAL)
                if summary.experiment:
                    ui.badge(summary.experiment, color=theme.SUCCESS)
                if not summary.complete:
                    ui.badge("incomplete", color=theme.WARNING)
            when = summary.started_at.strftime("%Y-%m-%d %H:%M") if summary.started_at else ""
            ui.label(f"{summary.n_responses} items · {when} · {summary.source}").classes(
                "text-xs"
            ).style(f"color:{theme.NEUTRAL}")

        # ``click.stop`` is the standard Quasar/Vue event modifier for cutting off
        # propagation to the card's own click handler above -- without it, deleting
        # a record would also open the record just deleted.
        delete_button = (
            ui.button(icon="delete").props("flat round dense").tooltip("Delete this record")
        )
        delete_button.on("click.stop", lambda: _confirm_delete(client, summary, redraw, on_change))


def _open(
    client,  # noqa: ANN001
    draft: DraftRecord,
    navigate: Callable[[str], None],
    on_change: Callable[[], None],
    session_id: int,
) -> None:
    """Load a stored record read-only and jump to the questionnaire tab.

    Args:
        client: The connection, for detached toasts.
        draft: The connection's draft to populate.
        navigate: Switches to another tab by name.
        on_change: Called after loading, so tab gating reflects the now-complete
            draft.
        session_id: The record's database id.
    """
    try:
        record = state.repository.load(session_id)
        draft.load_from(record, read_only=True)
    except Exception as exc:  # noqa: BLE001 - surface any load failure
        notify_detached(client, f"Could not load record: {exc}", colour=theme.DANGER)
        return

    on_change()
    navigate("questionnaire")


def _confirm_delete(
    client, summary, redraw: Callable[[], None], on_change: Callable[[], None]
) -> None:  # noqa: ANN001
    """Ask before deleting a record.

    Args:
        client: The connection, for detached toasts.
        summary: The record to delete.
        redraw: Rebuilds the listing afterwards.
        on_change: Called after the deletion.
    """
    with ui.dialog() as dialog, ui.card().classes("w-[26rem] max-w-full gap-2"):
        ui.label("Delete this record?").classes("text-lg font-medium")
        ui.label(
            f"Record {summary.session_id} for {summary.participant_code} "
            f"({summary.questionnaire}). This cannot be undone."
        ).classes("text-sm").style(f"color:{theme.NEUTRAL}")

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

            def confirm() -> None:
                """Delete and refresh."""
                state.delete(summary.session_id)
                dialog.close()
                redraw()
                on_change()
                notify_detached(
                    client, f"Deleted record {summary.session_id}.", colour=theme.NEUTRAL
                )

            ui.button("Delete", on_click=confirm).props("unelevated").style(
                f"background:{theme.DANGER}"
            )

    dialog.open()


def _start_new(
    draft: DraftRecord, navigate: Callable[[str], None], on_change: Callable[[], None]
) -> None:
    """Clear the draft and return to setup.

    Args:
        draft: The draft to reset.
        navigate: Switches to another tab by name.
        on_change: Called so tab gating updates.
    """
    draft.reset()
    on_change()
    navigate("setup")


def _export(client, instrument: str, shape: str) -> None:  # noqa: ANN001
    """Build an export file and hand it to the browser.

    Args:
        client: The connection, for detached toasts.
        instrument: Registry key to restrict to, or ``"all"``.
        shape: ``"wide"``, ``"long"`` or ``"json"``.
    """
    summaries = state.records()
    if instrument != _ALL:
        summaries = [s for s in summaries if s.questionnaire == instrument]
    session_ids = [s.session_id for s in summaries if s.complete]

    if not session_ids:
        notify_detached(client, "No complete records to export.", colour=theme.WARNING)
        return

    try:
        if shape == "json":
            text = json.dumps(export_module.to_json(state.repository, session_ids), indent=2)
            suffix = ".json"
        else:
            text = export_module.to_csv(state.repository.engine, session_ids, shape=shape)
            suffix = ".csv"
    except ValueError as exc:
        notify_detached(client, str(exc), colour=theme.WARNING)
        return

    name = (
        f"records-{instrument}-{shape}{suffix}"
        if instrument != _ALL
        else f"records-{shape}{suffix}"
    )
    target = Path(tempfile.gettempdir()) / name
    target.write_text(text, encoding="utf-8")
    ui.download.file(target, name)
