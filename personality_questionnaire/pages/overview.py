"""The landing tab: what this collects, and where to start."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire import registry
from personality_questionnaire.core import theme
from personality_questionnaire.pages.components import abbreviation_chip, card_style, feature_card

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["render"]

_FEATURES: tuple[tuple[str, str, str, str], ...] = (
    (
        "setup",
        "person_add",
        theme.PRIMARY,
        "Name the record and choose an instrument before the participant begins.",
    ),
    (
        "questionnaire",
        "checklist",
        theme.ACCENT,
        "Present every item and collect the answers, one screen at a time.",
    ),
    (
        "export",
        "save",
        theme.SUCCESS,
        "Review the computed scores and commit the record to the database.",
    ),
    (
        "records",
        "table_view",
        theme.NEUTRAL,
        "Browse everything collected so far and export the whole set as one file.",
    ),
)
"""Cards linking to the other tabs: ``(tab, icon, accent, description)``."""

_TITLES = {
    "setup": "Set up a record",
    "questionnaire": "Administer",
    "export": "Score and save",
    "records": "Records",
}
"""Card headings, keyed by tab."""


def render(navigate: Callable[[str], None]) -> None:
    """Build the overview tab.

    A landing page and nothing more: no live database numbers here, since a
    first-time visitor has not yet chosen a participant or an instrument for any
    count to mean something. Records and participant totals belong on the Records
    tab, where they are meaningful.

    Args:
        navigate: Switches to another tab by name.
    """
    with ui.column().classes("w-full items-center gap-6").style("padding:0.5rem 0 2rem"):
        with ui.column().classes("items-center gap-2"):
            ui.html(theme.LOGO_MARK_SVG).classes("w-16 h-16")
            ui.label("Personality Questionnaire").classes("text-3xl font-bold").style(
                f"color:{theme.PRIMARY}"
            )
            ui.label(
                "Administer validated personality and affect instruments, score them "
                "correctly, and keep every response with the provenance needed to "
                "reproduce it."
            ).classes("text-base text-center").style(f"color:{theme.NEUTRAL};max-width:38rem")

        with ui.row().classes("items-center gap-2 text-sm").style(f"color:{theme.NEUTRAL}"):
            ui.icon("bolt", size="1.1rem").style(f"color:{theme.ACCENT}")
            ui.label(
                "New here? Choose a database, name a participant, then answer the questionnaire."
            )

        ui.label("What you can do").classes("text-lg font-medium")
        with ui.element("div").style(
            "max-width:46rem;display:flex;flex-wrap:wrap;justify-content:center;"
            "align-items:stretch;gap:1rem"
        ):
            for tab, icon, accent, description in _FEATURES:
                feature_card(icon, accent, _TITLES[tab], description, lambda t=tab: navigate(t))

        _instruments()


def _instruments() -> None:
    """Render the shipped instruments with their citations."""
    with (
        ui.expansion("Instruments and citations", icon="menu_book")
        .classes("w-full")
        .style(f"max-width:46rem;{card_style()}")
    ):
        for key in registry.keys():
            instrument = registry.get(key)
            with ui.column().classes("gap-0 w-full").style("padding:0.4rem 0"):
                with ui.row().classes("items-center gap-2"):
                    abbreviation_chip(instrument.abbreviation)
                    ui.label(instrument.name).classes("font-medium")
                    ui.label(f"{instrument.n_items} items").classes("text-xs").style(
                        f"color:{theme.NEUTRAL}"
                    )
                ui.label(instrument.citation).classes("text-xs").style(f"color:{theme.NEUTRAL}")
