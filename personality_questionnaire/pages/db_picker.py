"""An async modal database picker.

This package runs locally, so the browser and the filesystem are the same machine:
the operator can navigate the real directory tree and pick a ``.db`` file instead of
typing its path. A thin NiceGUI view over the pure helpers in
:mod:`personality_questionnaire.core.dbpath`, following the same shape as Annie's
folder picker (open a dialog immediately with a spinner, resolve the listing off the
event loop, submit the chosen path through the dialog's own return value).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import background_tasks, run, ui

from personality_questionnaire.core import dbpath, theme

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

__all__ = ["pick_database"]


async def pick_database(start: Path) -> str | None:
    """Open a dialog for choosing an existing database or a location for a new one.

    Args:
        start: The directory to open the listing at.

    Returns:
        A ``sqlite:///...`` URL for the chosen file, or ``None`` if cancelled.
    """
    state: dict[str, Path | None] = {"dir": None}

    with ui.dialog() as dialog, ui.card().classes("w-[30rem] max-w-full"):
        ui.label("Select a database").classes("text-lg font-medium")
        path_label = (
            ui.label("Loading…").classes("text-xs break-all").style(f"color:{theme.NEUTRAL}")
        )
        listing = ui.column().classes("w-full gap-0 max-h-72 overflow-auto")

        def navigate(target: Path) -> None:
            background_tasks.create(load(target))

        async def load(target: Path) -> None:
            listing.clear()
            with listing:
                ui.spinner(size="lg").classes("self-center my-4")
            scanned = await run.io_bound(dbpath.scan_databases, target)
            if scanned is None:
                return  # the app is shutting down mid-scan
            subdirs, files = scanned
            state["dir"] = target
            path_label.set_text(str(target))
            listing.clear()
            with listing:
                parent = dbpath.parent_of(target)
                if parent is not None:
                    _entry_row("arrow_upward", "..", lambda: navigate(parent), muted=True)
                for child in subdirs:
                    _entry_row(
                        "folder", child.name, lambda c=child: navigate(c), colour=theme.PRIMARY
                    )
                for child in files:
                    _entry_row(
                        "storage", child.name, lambda c=child: choose_file(c), colour=theme.SUCCESS
                    )

        def choose_file(chosen: Path) -> None:
            dialog.submit(f"sqlite:///{chosen}")

        def choose_here() -> None:
            directory = state["dir"]
            if directory is None:
                return
            with ui.dialog() as name_dialog, ui.card().classes("w-[24rem] max-w-full gap-2"):
                ui.label("New database name").classes("text-base font-medium")
                name_input = ui.input("Filename", value="records.db").props("dense outlined")
                with ui.row().classes("justify-end gap-2 w-full"):
                    ui.button("Cancel", on_click=name_dialog.close).props("flat")

                    def confirm() -> None:
                        filename = (name_input.value or "records.db").strip()
                        name_dialog.close()
                        dialog.submit(f"sqlite:///{directory / filename}")

                    ui.button("Create", on_click=confirm).props("unelevated").style(
                        f"background:{theme.PRIMARY}"
                    )
            name_dialog.open()

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat")
            ui.button("New database here", icon="add", on_click=choose_here).props("flat")

    background_tasks.create(load(start))
    dialog.open()
    return await dialog


def _entry_row(
    icon: str,
    label: str,
    on_click: Callable[[], None],
    *,
    colour: str | None = None,
    muted: bool = False,
) -> None:
    """Render one clickable directory/file row inside the picker listing.

    Args:
        icon: Material icon name.
        label: The entry's display name.
        on_click: Called when the row is clicked.
        colour: Icon colour.
        muted: Whether to render the label in the secondary colour.
    """
    row = ui.row().classes("w-full items-center gap-2 cursor-pointer p-1 rounded hover:bg-gray-200")
    row.on("click", lambda: on_click())
    with row:
        ui.icon(icon, color=colour or theme.NEUTRAL)
        text = ui.label(label).classes("text-sm")
        if muted:
            text.style(f"color:{theme.NEUTRAL}")
