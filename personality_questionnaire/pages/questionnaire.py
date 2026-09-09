"""The administration tab: present every item and collect answers.

The widget follows the instrument's scale type -- radio buttons carrying the
published response labels for a Likert form, a slider between the item's own anchors
for a visual-analogue one -- so a participant sees the instrument as its authors
wrote it rather than a row of bare numbers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire.core import theme
from personality_questionnaire.pages.components import card_style
from personality_questionnaire.registry import ScaleType

if TYPE_CHECKING:
    from collections.abc import Callable

    from personality_questionnaire.core.state import DraftRecord

__all__ = ["render"]


def render(
    draft: DraftRecord, navigate: Callable[[str], None], on_change: Callable[[], None]
) -> None:
    """Build the questionnaire tab.

    Args:
        draft: The connection's draft record.
        navigate: Switches to another tab by name.
        on_change: Called after each answer, so gating and progress stay current.
    """
    instrument = draft.instrument
    if instrument is None:
        _placeholder(navigate)
        return

    with ui.column().classes("w-full items-center gap-3"):
        if draft.read_only:
            _read_only_banner(draft, navigate)

        header = ui.column().classes("w-full gap-1").style("max-width:64rem")
        with header:
            ui.label(instrument.name).classes("text-lg font-medium")
            if instrument.labels:
                ui.label(
                    " · ".join(
                        f"{value} {label}"
                        for label, value in sorted(
                            instrument.labels.items(), key=lambda pair: pair[1]
                        )
                    )
                ).classes("text-xs").style(f"color:{theme.NEUTRAL}")

            progress = (
                ui.linear_progress(value=draft.progress, show_value=False)
                .props("rounded size=10px")
                .style(f"color:{theme.ACCENT}")
            )
            counter = ui.label().classes("text-sm").style(f"color:{theme.NEUTRAL}")

        items = ui.column().classes("w-full gap-2").style("max-width:64rem")

        footer = ui.row().classes("w-full justify-end gap-2").style("max-width:64rem")
        with footer:
            finish = (
                ui.button("Review and save", icon="arrow_forward")
                .props("unelevated")
                .style(f"background:{theme.PRIMARY}")
            )

    def update() -> None:
        """Refresh progress, the counter and the finish button."""
        progress.set_value(draft.progress)
        counter.set_text(f"{draft.answered} of {draft.n_items} answered")
        finish.set_enabled(draft.complete)
        on_change()

    with items:
        for item in instrument.items:
            _item_row(draft, item, update)

    finish.on_click(lambda: navigate("export"))
    update()


def _read_only_banner(draft: DraftRecord, navigate: Callable[[str], None]) -> None:
    """Show that a loaded record is being viewed, with a way to unlock it.

    Args:
        draft: The loaded draft.
        navigate: Switches to another tab by name -- reused here to trigger a
            same-tab rebuild once unlocked, exploiting the same
            ``if tabs.value == name: rebuild(name)`` branch a real tab click uses.
    """
    with (
        ui.row()
        .classes("w-full items-center gap-3 no-wrap")
        .style(
            f"max-width:64rem;background:{theme.WARNING}1a;border:1px solid {theme.WARNING}55;"
            "border-radius:8px;padding:0.5rem 1rem"
        )
    ):
        ui.icon("visibility", size="1.2rem").style(f"color:{theme.WARNING}")
        ui.label(
            f"Viewing record #{draft.loaded_session_id} for {draft.participant_code} "
            f"({draft.tag or 'no tag'}) — read-only."
        ).classes("flex-grow text-sm")

        def edit() -> None:
            """Unlock the draft and rebuild this tab live-editable."""
            draft.unlock()
            navigate("questionnaire")

        ui.button("Edit this record", icon="edit", on_click=edit).props("flat dense")


def _placeholder(navigate: Callable[[str], None]) -> None:
    """Explain that setup comes first.

    Args:
        navigate: Switches to another tab by name.
    """
    with ui.column().classes("w-full items-center gap-3").style("padding-top:3rem"):
        ui.icon("checklist", size="3rem").style(f"color:{theme.NEUTRAL}")
        ui.label("Choose a participant and an instrument first.").classes("text-base")
        ui.button("Go to setup", on_click=lambda: navigate("setup")).props("flat")


def _item_row(draft: DraftRecord, item, update: Callable[[], None]) -> None:  # noqa: ANN001
    """Render one item and its response widget.

    Args:
        draft: The draft to write the answer into.
        item: The item being presented.
        update: Called after the answer changes.
    """
    instrument = draft.instrument
    assert instrument is not None  # noqa: S101 - guarded by the caller

    card = ui.card().classes("w-full gap-2").style(card_style())

    def mark_answered() -> None:
        """Tint the card's border once the item has an answer."""
        answered = item.number in draft.responses
        colour = theme.SUCCESS if answered else "#DCD9D2"
        card.style(f"border:1px solid {colour};border-left:4px solid {colour};border-radius:10px")

    with card:

        def record(value: int) -> None:
            """Store one answer and refresh the interface."""
            draft.answer(item.number, int(value))
            mark_answered()
            update()

        if instrument.scale is ScaleType.LIKERT:
            # Label and options share one row: the label takes the space it needs
            # and the option group is pinned to the right edge with flex-wrap
            # explicitly disabled. Quasar's "inline" prop alone keeps each option
            # from being block-level, but does not guarantee one line -- without
            # the explicit nowrap, a 5-option group wraps under the label the
            # moment the item text runs long, which is the common case for every
            # 5-point Likert instrument shipped here.
            with ui.row().classes("items-center justify-between gap-4 no-wrap w-full"):
                with (
                    ui.row()
                    .classes("items-baseline gap-2 no-wrap")
                    .style("flex:1 1 40%;min-width:12rem")
                ):
                    ui.label(f"{item.number}.").classes("text-sm").style(
                        f"color:{theme.NEUTRAL};min-width:2rem"
                    )
                    ui.label(item.text).classes("text-base")

                options = {
                    value: label
                    for label, value in sorted(instrument.labels.items(), key=lambda p: p[1])
                }
                radio = (
                    ui.radio(
                        options,
                        value=draft.responses.get(item.number),
                        on_change=None if draft.read_only else (lambda e: record(e.value)),
                    )
                    .props("inline dense")
                    .classes("text-sm")
                    .style("display:flex;flex-wrap:nowrap;justify-content:flex-end;gap:0.75rem")
                )
                if draft.read_only:
                    radio.props("disable")
        else:
            with ui.row().classes("items-baseline gap-2 no-wrap w-full"):
                ui.label(f"{item.number}.").classes("text-sm").style(
                    f"color:{theme.NEUTRAL};min-width:2rem"
                )
                ui.label(item.text).classes("text-base flex-grow")
            with ui.row().classes("items-center gap-3 no-wrap w-full"):
                ui.label(item.low_anchor).classes("text-xs").style(
                    f"color:{theme.NEUTRAL};min-width:9rem;text-align:right"
                )
                slider = ui.slider(
                    min=instrument.minimum,
                    max=instrument.maximum,
                    step=1,
                    value=draft.responses.get(item.number, instrument.minimum),
                ).classes("flex-grow")
                if draft.read_only:
                    slider.props("disable")
                ui.label(item.high_anchor).classes("text-xs").style(
                    f"color:{theme.NEUTRAL};min-width:9rem"
                )
                ui.label().bind_text_from(slider, "value").classes("text-sm font-medium").style(
                    "min-width:1.5rem"
                )
            if not draft.read_only:
                slider.on("change", lambda e: record(e.args))

    mark_answered()
