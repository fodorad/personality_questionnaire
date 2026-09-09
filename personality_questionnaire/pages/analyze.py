"""The analyze tab: psychometric diagnostics over collected records."""

from __future__ import annotations

import numpy as np
from nicegui import ui

from personality_questionnaire import analysis, registry
from personality_questionnaire.core import theme
from personality_questionnaire.core.state import state
from personality_questionnaire.pages.components import card_style, metric_card, metric_grid

__all__ = ["render"]

_MIN_RECORDS = 2
"""Fewest complete records reliability and descriptives can be computed from."""

_METRICS = ("Reliability", "Descriptives")


def render() -> None:
    """Build the analyze tab."""
    keys = list(registry.keys())
    chosen = {"instrument": keys[0], "metric": _METRICS[0]}

    with ui.column().classes("w-full items-center gap-3").style("padding-top:0.5rem"):
        with ui.row().classes("w-full items-center gap-2 no-wrap").style("max-width:52rem"):
            instrument_select = (
                ui.select({k: k for k in keys}, value=chosen["instrument"], label="Instrument")
                .props("dense outlined")
                .classes("w-40")
            )
            metric_toggle = ui.toggle(list(_METRICS), value=chosen["metric"]).props("dense")

        body = ui.column().classes("w-full gap-2").style("max-width:52rem")

    def redraw() -> None:
        """Recompute and render diagnostics for the current selection."""
        body.clear()
        instrument = registry.get(chosen["instrument"])
        _, answers = state.repository.responses_for(chosen["instrument"])

        with body:
            if len(answers) < _MIN_RECORDS:
                _too_few(len(answers))
                return
            if chosen["metric"] == "Reliability":
                _render_reliability(instrument, np.array(answers))
            else:
                _render_descriptives(instrument, np.array(answers))

    def instrument_changed(event) -> None:  # noqa: ANN001 - NiceGUI event argument
        chosen["instrument"] = event.value
        redraw()

    def metric_changed(event) -> None:  # noqa: ANN001 - NiceGUI event argument
        chosen["metric"] = event.value
        redraw()

    instrument_select.on_value_change(instrument_changed)
    metric_toggle.on_value_change(metric_changed)
    redraw()


def _render_reliability(instrument: registry.Questionnaire, answers: np.ndarray) -> None:
    """Render Cronbach's alpha and the weakest item-total correlation per subscale.

    Args:
        instrument: The instrument being analyzed.
        answers: Raw responses, shape ``(n_participants, n_items)``.
    """
    reliability = analysis.subscale_reliability(instrument, answers)
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
                r = reliability[subscale.name]
                weakest = min(r.item_total_correlations, default=0.0)
                _reliability_card(subscale.name, r.alpha, weakest, colour)


def _reliability_card(title: str, alpha: float, weakest: float, colour: str) -> None:
    """Render one subscale's alpha, with its weakest item-total correlation below.

    Args:
        title: The subscale's display name.
        alpha: Cronbach's alpha.
        weakest: The lowest item-total correlation among its items.
        colour: Caption colour, from the theme.
    """
    with ui.card().classes("flex-1 min-w-[8rem]").style(card_style()):
        ui.label(title).classes("text-sm").style(f"color:{colour}")
        ui.label(f"α = {alpha:.3f}").classes("text-2xl font-medium")
        ui.label(f"weakest item {weakest:.3f}").classes("text-xs").style(f"color:{theme.NEUTRAL}")


def _render_descriptives(instrument: registry.Questionnaire, answers: np.ndarray) -> None:
    """Render mean, sd and range of each subscale's scores.

    Args:
        instrument: The instrument being analyzed.
        answers: Raw responses, shape ``(n_participants, n_items)``.
    """
    from personality_questionnaire import scoring

    result = scoring.score(instrument, answers)
    described = analysis.describe(result.names, result.values)
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
                d = described[subscale.name]
                metric_card(subscale.name, f"{d.mean:.3f} ± {d.sd:.3f}", colour)


def _too_few(n: int) -> None:
    """Explain why diagnostics cannot be computed yet.

    Args:
        n: How many complete records exist for the chosen instrument.
    """
    with ui.column().classes("w-full items-center gap-2").style("padding-top:2rem"):
        ui.icon("query_stats", size="2.5rem").style(f"color:{theme.NEUTRAL}")
        ui.label(
            f"Need at least {_MIN_RECORDS} complete records for this instrument "
            f"to compute diagnostics -- found {n}."
        ).classes("text-sm text-center").style(f"color:{theme.NEUTRAL};max-width:26rem")
