"""The setup tab: who is answering, and which instrument."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire import registry
from personality_questionnaire.core import dbpath, recent_databases, theme
from personality_questionnaire.core.state import state
from personality_questionnaire.pages.components import card_style, notify_detached, section_title
from personality_questionnaire.pages.db_picker import pick_database

if TYPE_CHECKING:
    from collections.abc import Callable

    from personality_questionnaire.core.state import DraftRecord

__all__ = ["render"]


def render(
    draft: DraftRecord, navigate: Callable[[str], None], on_change: Callable[[], None]
) -> None:
    """Build the setup tab.

    Args:
        draft: The connection's draft record, written to as fields change.
        navigate: Switches to another tab by name.
        on_change: Called whenever the draft's readiness may have changed, so the
            tab bar can enable or disable the questionnaire tab.
    """
    from nicegui import context

    client = context.client

    with ui.column().classes("w-full items-center gap-4").style("padding-top:0.5rem"):
        db_card = ui.card().classes("w-full gap-3").style(f"max-width:40rem;{card_style()}")
        _render_database_card(client, draft, db_card)

        with ui.card().classes("w-full gap-3").style(f"max-width:40rem;{card_style()}"):
            section_title(
                "Participant",
                hint="Use a study-local code. Records are pseudonymous by default; "
                "do not enter a name.",
            )

            code = (
                ui.input("Participant code", value=draft.participant_code)
                .props("dense outlined")
                .classes("w-full")
            )
            label = (
                ui.input("Label (optional)", value=draft.participant_label)
                .props("dense outlined")
                .classes("w-full")
            )

            with ui.row().classes("w-full gap-3 no-wrap"):
                experiment = (
                    ui.input("Experiment (optional)", value=draft.experiment)
                    .props("dense outlined")
                    .classes("flex-1")
                )
                tag = (
                    ui.input("Tag (optional)", value=draft.tag)
                    .props("dense outlined")
                    .classes("flex-1")
                )

            ui.label(
                'A tag distinguishes repeated administrations, such as "pre" and "post".'
            ).classes("text-xs").style(f"color:{theme.NEUTRAL}")

        with ui.card().classes("w-full gap-3").style(f"max-width:40rem;{card_style()}"):
            section_title("Instrument", hint="What the participant will answer.")

            options = {
                key: f"{registry.get(key).name}  ({registry.get(key).n_items} items)"
                for key in registry.keys()
            }
            chooser = (
                ui.select(options, value=draft.questionnaire_key, label="Questionnaire")
                .props("dense outlined")
                .classes("w-full")
            )

            detail = ui.column().classes("gap-1 w-full")

        start = (
            ui.button("Start questionnaire", icon="arrow_forward")
            .props("unelevated")
            .style(f"background:{theme.PRIMARY}")
        )

    def refresh_detail() -> None:
        """Redraw the chosen instrument's summary."""
        detail.clear()
        instrument = draft.instrument
        if instrument is None:
            return
        with detail:
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.badge(f"{instrument.minimum}–{instrument.maximum} scale", color=theme.PRIMARY)
                for subscale in instrument.subscales_at(instrument.levels[0]):
                    ui.badge(subscale.name, color=theme.NEUTRAL)
            ui.label(instrument.citation).classes("text-xs").style(f"color:{theme.NEUTRAL}")

    def sync() -> None:
        """Push field values into the draft and update dependent widgets."""
        draft.participant_code = code.value or ""
        draft.participant_label = label.value or ""
        draft.experiment = experiment.value or ""
        draft.tag = tag.value or ""
        start.set_enabled(draft.ready)
        on_change()

    def choose(event) -> None:  # noqa: ANN001 - NiceGUI event argument
        """Change instrument, confirming first if answers would be lost."""
        new_key = event.value
        if new_key == draft.questionnaire_key:
            return

        if draft.responses:
            _confirm_change(draft, new_key, chooser, refresh_detail, sync)
            return

        draft.questionnaire_key = new_key
        refresh_detail()
        sync()

    for field in (code, label, experiment, tag):
        field.on("blur", lambda _: sync())
        field.on("keydown.enter", lambda _: sync())
    chooser.on_value_change(choose)
    start.on_click(lambda: navigate("questionnaire"))

    refresh_detail()
    sync()


def _render_database_card(client, draft: DraftRecord, card: ui.card) -> None:  # noqa: ANN001
    """Build the database card: active path, availability, browse, and recent.

    Args:
        client: The connection, for detached toasts.
        draft: The connection's draft, checked before switching databases.
        card: The card to render into.
    """
    with card:
        section_title("Database", hint="Where records are stored.")

        with ui.row().classes("w-full items-center gap-2 no-wrap"):
            path_input = (
                ui.input("Database path", value=state.database_url or "")
                .props("dense outlined")
                .classes("flex-grow")
            )
            status = ui.badge("", color=theme.SUCCESS)
            browse_button = (
                ui.button(icon="folder_open")
                .props("flat round dense")
                .tooltip("Browse for a database file")
            )

        recent_list = ui.column().classes("w-full gap-1")

    def refresh() -> None:
        """Redraw the availability badge, path field and recent-database list."""
        url = state.database_url or ""
        path_input.set_value(url)
        exists = url.startswith("sqlite:///") and Path(url.removeprefix("sqlite:///")).exists()
        status.set_text("available" if exists else "will be created")
        status.props(f"color={theme.SUCCESS if exists else theme.NEUTRAL}")

        recent_list.clear()
        entries = recent_databases.load_recent()
        if not entries:
            return
        with recent_list:
            ui.label("Recent databases").classes("text-xs").style(f"color:{theme.NEUTRAL}")
            for entry in entries:
                _recent_row(entry, apply_url)

    def apply_url(url: str) -> None:
        """Switch to a database, warning first if it would strand a draft's context.

        The draft itself is untouched by a database switch -- only where records
        are read from and written to changes -- but an operator mid-questionnaire
        should know the records list they see afterwards is a different one.
        """
        if url == state.database_url:
            return
        if draft.responses:
            notify_detached(
                client,
                "Switched database. The current draft is unaffected, but the "
                "records list now reflects the new database.",
                colour=theme.NEUTRAL,
            )
        try:
            state.set_database(url)
        except Exception as exc:  # noqa: BLE001 - surface any storage failure
            notify_detached(client, f"Could not open database: {exc}", colour=theme.DANGER)
            return
        refresh()

    async def browse() -> None:
        """Open the picker and apply whatever was chosen."""
        chosen = await pick_database(dbpath.resolve_start_dir(state.database_url))
        if chosen is not None:
            apply_url(chosen)

    def on_path_edited() -> None:
        """Apply an edited path once it looks like a usable database."""
        url = (path_input.value or "").strip()
        if url and dbpath.is_valid_sqlite_url(url):
            apply_url(url)

    browse_button.on_click(browse)
    path_input.on("blur", lambda: on_path_edited())
    path_input.on("keydown.enter", lambda: on_path_edited())

    refresh()


def _recent_row(url: str, on_choose: Callable[[str], None]) -> None:
    """Render one clickable recent-database row.

    Args:
        url: The database URL this row represents.
        on_choose: Called with ``url`` when the row is clicked.
    """
    is_active = url == state.database_url
    row = ui.row().classes("w-full items-center gap-2 cursor-pointer p-1 rounded hover:bg-gray-200")
    row.on("click", lambda: on_choose(url))
    with row:
        ui.icon(
            "check_circle" if is_active else "storage",
            color=theme.SUCCESS if is_active else theme.NEUTRAL,
        )
        label = ui.label(url.removeprefix("sqlite:///")).classes("text-sm break-all")
        if is_active:
            label.classes("font-medium")


def _confirm_change(
    draft: DraftRecord,
    new_key: str,
    chooser: ui.select,
    refresh_detail: Callable[[], None],
    sync: Callable[[], None],
) -> None:
    """Ask before discarding answers to switch instruments.

    Args:
        draft: The draft that holds the answers.
        new_key: The instrument being switched to.
        chooser: The select to revert if the operator declines.
        refresh_detail: Redraws the instrument summary.
        sync: Re-reads the form into the draft.
    """
    with ui.dialog() as dialog, ui.card().classes("w-[28rem] max-w-full gap-2"):
        ui.label("Discard the answers so far?").classes("text-lg font-medium")
        ui.label(
            f"{draft.answered} answer(s) have been recorded for "
            f"{draft.questionnaire_key}. Changing instrument clears them."
        ).classes("text-sm").style(f"color:{theme.NEUTRAL}")

        with ui.row().classes("justify-end gap-2 w-full"):

            def keep() -> None:
                """Revert the selection and close."""
                chooser.set_value(draft.questionnaire_key)
                dialog.close()

            def discard() -> None:
                """Switch instrument and clear the answers."""
                draft.questionnaire_key = new_key
                draft.clear_responses()
                refresh_detail()
                sync()
                dialog.close()

            ui.button("Keep answers", on_click=keep).props("flat")
            ui.button("Discard", on_click=discard).props("unelevated").style(
                f"background:{theme.DANGER}"
            )

    dialog.open()
