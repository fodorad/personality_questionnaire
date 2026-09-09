"""The scoring tab: show what was computed, then commit the record."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from personality_questionnaire.core import theme
from personality_questionnaire.core.state import state
from personality_questionnaire.pages.components import (
    card_style,
    metric_card,
    metric_grid,
    notify_detached,
)
from personality_questionnaire.provenance import capture

if TYPE_CHECKING:
    from collections.abc import Callable

    from personality_questionnaire.core.state import DraftRecord
    from personality_questionnaire.registry import Questionnaire
    from personality_questionnaire.scoring import ScoreResult

__all__ = ["render"]


def render(
    draft: DraftRecord, navigate: Callable[[str], None], on_change: Callable[[], None]
) -> None:
    """Build the export tab.

    Args:
        draft: The connection's draft record.
        navigate: Switches to another tab by name.
        on_change: Called after saving, so other tabs pick up the new record.
    """
    if not draft.complete:
        _incomplete(draft, navigate)
        return

    from nicegui import context

    client = context.client
    result = draft.score()
    instrument = draft.instrument
    assert instrument is not None  # noqa: S101 - complete implies an instrument

    with ui.column().classes("w-full items-center gap-4").style("padding-top:0.5rem"):
        with ui.card().classes("w-full gap-3").style(f"max-width:56rem;{card_style()}"):
            with ui.row().classes("items-center gap-2 w-full"):
                ui.label(instrument.name).classes("text-lg font-medium flex-grow")
                ui.badge(draft.participant_code, color=theme.PRIMARY)
                if draft.tag:
                    ui.badge(draft.tag, color=theme.NEUTRAL)
                if draft.loaded_session_id is not None:
                    ui.badge(
                        f"record #{draft.loaded_session_id}"
                        if draft.read_only
                        else f"editing #{draft.loaded_session_id}",
                        color=theme.NEUTRAL,
                    )

            if _is_domain_grouped(instrument):
                _render_grouped(instrument, result)
            else:
                _render_flat(instrument, result)

        _provenance()

        with ui.row().classes("gap-2"):
            save_label = "Save changes" if draft.loaded_session_id is not None else "Save record"
            save = (
                ui.button(save_label, icon="save")
                .props("unelevated")
                .style(f"background:{theme.SUCCESS}")
            )
            ui.button("Back to questionnaire", on_click=lambda: navigate("questionnaire")).props(
                "flat"
            )

        if draft.read_only:
            save.set_enabled(False)
            ui.label(
                "This record is read-only. Edit it from the Questionnaire tab to save changes."
            ).classes("text-xs").style(f"color:{theme.NEUTRAL}")

    def commit() -> None:
        """Store the record, then move on to the records tab."""
        try:
            if draft.loaded_session_id is not None:
                saved = state.update(draft.loaded_session_id, draft.to_record())
                message = f"Updated record {saved.session_id}."
            else:
                saved = state.save(draft.to_record())
                message = f"Saved record {saved.session_id}."
        except Exception as exc:  # noqa: BLE001 - surface any storage failure
            notify_detached(client, f"Could not save: {exc}", colour=theme.DANGER)
            return

        draft.reset()
        on_change()
        notify_detached(client, message, colour=theme.SUCCESS)
        navigate("records")

    save.on_click(commit)


def _is_domain_grouped(instrument: Questionnaire) -> bool:
    """Whether an instrument has a domain/facet hierarchy worth grouping visually.

    True only when there is more than one level and every subscale past the first
    names a parent -- BFI-2's facets, all parented to a domain. PANAS's second
    level (`published total`) is an alternate aggregation of the *same* two
    scales, not a child grouping, and carries no parent, so it is correctly
    excluded and renders through the flat path instead.

    Args:
        instrument: The instrument to check.

    Returns:
        True if its non-first levels are all parented.
    """
    if len(instrument.levels) <= 1:
        return False
    later_subscales = [s for level in instrument.levels[1:] for s in instrument.subscales_at(level)]
    return bool(later_subscales) and all(s.parent is not None for s in later_subscales)


def _render_grouped(instrument: Questionnaire, result: ScoreResult) -> None:
    """Render one tinted block per top-level (domain) subscale, facets nested inside.

    Args:
        instrument: The instrument being displayed.
        result: Its computed scores.
    """
    values = result.as_dict()
    top_level, *child_levels = instrument.levels
    domains = instrument.subscales_at(top_level)

    with metric_grid(min_column_width="14rem"):
        for domain in domains:
            colour = theme.domain_color(domain.name, None)
            with ui.element("div").style(
                f"border-left:4px solid {colour};border-radius:8px;"
                f"background:{colour}0d;padding:0.75rem;"
                "display:flex;flex-direction:column;gap:0.5rem"
            ):
                metric_card(domain.name, f"{values[domain.name]:.3f}", colour)
                children = [
                    s
                    for level in child_levels
                    for s in instrument.subscales_at(level)
                    if s.parent == domain.name
                ]
                if children:
                    with metric_grid(min_column_width="6rem"):
                        for child in children:
                            metric_card(
                                child.name,
                                f"{values[child.name]:.3f}",
                                theme.domain_color(child.name, child.parent),
                            )


def _render_flat(instrument: Questionnaire, result: ScoreResult) -> None:
    """Render one equal-width row of cards per level.

    Args:
        instrument: The instrument being displayed.
        result: Its computed scores.
    """
    values = result.as_dict()
    for level in instrument.levels:
        subscales = instrument.subscales_at(level)
        if not subscales:
            continue
        ui.label(level.title()).classes("text-sm font-medium").style(
            f"color:{theme.NEUTRAL};padding-top:0.3rem"
        )
        with metric_grid():
            for subscale in subscales:
                colour = theme.domain_color(subscale.name, subscale.parent)
                metric_card(subscale.name, f"{values[subscale.name]:.3f}", colour)


def _incomplete(draft: DraftRecord, navigate: Callable[[str], None]) -> None:
    """Explain what remains before a record can be saved.

    Args:
        draft: The draft being checked.
        navigate: Switches to another tab by name.
    """
    with ui.column().classes("w-full items-center gap-3").style("padding-top:3rem"):
        ui.icon("pending_actions", size="3rem").style(f"color:{theme.WARNING}")
        if draft.instrument is None:
            ui.label("Choose a participant and an instrument first.").classes("text-base")
            ui.button("Go to setup", on_click=lambda: navigate("setup")).props("flat")
            return

        remaining = draft.missing
        ui.label(
            f"{len(remaining)} item(s) still unanswered: "
            f"{', '.join(str(n) for n in remaining[:12])}"
            f"{'…' if len(remaining) > 12 else ''}"
        ).classes("text-base text-center").style("max-width:30rem")
        ui.button("Back to questionnaire", on_click=lambda: navigate("questionnaire")).props("flat")


def _provenance() -> None:
    """Show what will be recorded alongside the scores."""
    snapshot = capture()
    parts = [f"v{snapshot.package_version}"]
    if snapshot.git_sha:
        parts.append(snapshot.git_sha[:8] + (" (dirty)" if snapshot.git_dirty else ""))

    with ui.row().classes("items-center gap-2"):
        ui.icon("fingerprint", size="1rem").style(f"color:{theme.NEUTRAL}")
        ui.label("Recorded with " + " · ".join(parts)).classes("text-xs").style(
            f"color:{theme.NEUTRAL}"
        )
