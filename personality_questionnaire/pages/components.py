"""Shared interface pieces.

Everything visual is built from theme tokens rather than literal colours, so a
redesign touches :mod:`personality_questionnaire.core.theme` alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire.core import theme

if TYPE_CHECKING:
    from collections.abc import Callable

    from nicegui import Client

__all__ = [
    "abbreviation_chip",
    "card_style",
    "feature_card",
    "metric_card",
    "metric_grid",
    "notify_detached",
    "section_title",
]


def card_style() -> str:
    """Return the inline style every list row and card carries.

    Returns:
        A CSS declaration string.
    """
    return f"border:{theme.ROW_BORDER};border-radius:10px"


def section_title(text: str, *, hint: str = "") -> None:
    """Render a section heading with an optional explanatory line.

    Args:
        text: The heading.
        hint: A sentence shown beneath it, in the secondary colour.
    """
    ui.label(text).classes("text-lg font-medium")
    if hint:
        ui.label(hint).classes("text-sm").style(f"color:{theme.NEUTRAL}")


def abbreviation_chip(text: str, *, colour: str = theme.PRIMARY) -> None:
    """Render a small formatted box for an instrument's literature abbreviation.

    A citation-style label (``"BFI-2-XS"``) rather than a generic status pill, so
    the instrument list reads as a reference table rather than a set of tags.

    Args:
        text: The abbreviation to show, e.g. ``"BFI-2-XS"``.
        colour: The chip's accent colour.
    """
    with ui.element("div").style(
        "display:inline-flex;align-items:center;padding:0.15rem 0.6rem;"
        f"border-radius:6px;background:{colour}1a;border:1px solid {colour}33"
    ):
        ui.label(text).classes("text-xs font-semibold").style(
            f"color:{colour};letter-spacing:0.02em"
        )


def metric_grid(min_column_width: str = "9rem") -> ui.element:
    """Build a CSS grid container for a row of equal-width metric cards.

    A flex row with ``flex-wrap`` sizes each card to its own content, so a row of
    differently-named subscales never lines up. Grid tracks are equal-width by
    construction regardless of how many cards a given row holds -- 2 for VAS-F,
    5 for the BFI-2 domains -- which is what "one row, because the traits are
    equal" actually requires.

    Args:
        min_column_width: The narrowest a column may get before wrapping to a new
            row, e.g. ``"9rem"`` for a full domain row, smaller for a nested facet
            row.

    Returns:
        The grid element. Add :func:`metric_card` calls inside a ``with`` block.
    """
    return ui.element("div").style(
        "display:grid;"
        f"grid-template-columns:repeat(auto-fit, minmax({min_column_width}, 1fr));"
        "gap:0.5rem;width:100%"
    )


def metric_card(title: str, value: str, colour: str) -> ui.label:
    """Render one statistic tile.

    Args:
        title: The caption above the number.
        value: The number, already formatted.
        colour: Caption colour, from the theme.

    Returns:
        The value label, so a caller can update it in place.
    """
    with ui.card().classes("flex-1 min-w-[8rem]").style(card_style()):
        ui.label(title).classes("text-sm").style(f"color:{colour}")
        return ui.label(value).classes("text-2xl font-medium")


def feature_card(
    icon: str,
    accent: str,
    title: str,
    description: str,
    on_open: Callable[[], None],
) -> None:
    """Render one clickable capability card.

    Args:
        icon: Material icon name.
        accent: Accent colour for the icon tile.
        title: Card heading.
        description: One sentence beneath the heading.
        on_open: Called when the card is clicked.
    """
    card = (
        ui.card()
        .classes(
            "w-[21rem] cursor-pointer gap-2 transition-all duration-200 "
            "hover:-translate-y-0.5 hover:shadow-lg"
        )
        .style(f"{card_style()};align-self:stretch")
    )
    card.on("click", lambda: on_open())
    with card:
        with ui.row().classes("items-center gap-3 no-wrap w-full"):
            with ui.element("div").style(
                f"width:44px;height:44px;border-radius:11px;display:flex;"
                f"align-items:center;justify-content:center;background:{accent}1a"
            ):
                ui.icon(icon, size="1.6rem").style(f"color:{accent}")
            ui.label(title).classes("text-lg font-medium flex-grow")
            ui.icon("arrow_forward", size="1.1rem").style(f"color:{theme.NEUTRAL}")
        ui.label(description).classes("text-sm leading-snug").style(f"color:{theme.NEUTRAL}")


def notify_detached(client: Client, message: str, *, colour: str) -> None:
    """Show a toast from a handler that tore down the slot it ran in.

    ``ui.notify`` resolves its client through the slot the handler runs in, which
    NiceGUI takes from the sender's parent element. A handler that refreshes the
    container holding its own button drops that parent, so a later notify dies with
    "the parent element this slot belongs to has been deleted". Re-entering the
    client lands in its long-lived content slot instead.

    Args:
        client: The connection to notify.
        message: The text to show.
        colour: Background colour, from the theme.
    """
    with client:
        ui.notify(message, color=colour)
