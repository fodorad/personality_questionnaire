"""Rendering a computed score as a matplotlib figure.

Big Five instruments (five equal domains) read best as a radar chart; every other
instrument here has two or three unrelated scales, which a radar would misleadingly
imply are comparable axes of one shape, so those get a plain bar chart instead.
Both paths pull their colours from :mod:`personality_questionnaire.core.theme`, so
the demo reads as the same application as the Lab UI.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from personality_questionnaire.core import theme

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from personality_questionnaire.registry import Questionnaire
    from personality_questionnaire.scoring import ScoreResult

__all__ = ["is_big_five", "plot_for"]

_BIG_FIVE_DOMAINS = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)


def is_big_five(questionnaire: Questionnaire) -> bool:
    """Whether an instrument's top-level subscales are exactly the five domains.

    Args:
        questionnaire: The instrument to check.

    Returns:
        True if its first level is exactly the five Big Five domains, in any order.
    """
    top_level = questionnaire.subscales_at(questionnaire.levels[0])
    return {s.name for s in top_level} == set(_BIG_FIVE_DOMAINS)


def plot_for(questionnaire: Questionnaire, result: ScoreResult) -> Figure:
    """Render the right chart for one instrument's computed scores.

    Args:
        questionnaire: The instrument that was scored.
        result: Its computed scores, for a single participant.

    Returns:
        A matplotlib figure the caller owns and must close when done with it.
    """
    if is_big_five(questionnaire):
        return _radar_chart(result)
    return _bar_chart(result)


def _radar_chart(result: ScoreResult) -> Figure:
    """Draw the five Big Five domains as a pentagon radar.

    Args:
        result: Computed domain scores, normalized to ``[0, 1]``.

    Returns:
        The figure.
    """
    values = result.as_dict()
    domains = [d for d in _BIG_FIVE_DOMAINS if d in values]
    scores = [values[d] for d in domains]
    colours = [theme.DOMAIN_COLORS[d] for d in domains]

    angles = [n / len(domains) * 2 * math.pi for n in range(len(domains))]
    angles += angles[:1]
    scores_closed = scores + scores[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor(theme.PAPER)
    ax.set_facecolor(theme.PAPER)

    ax.plot(angles, scores_closed, color=theme.PRIMARY, linewidth=2)
    ax.fill(angles, scores_closed, color=theme.ACCENT, alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([d.capitalize() for d in domains], color=theme.INK, fontsize=11)
    for tick_label, colour in zip(ax.get_xticklabels(), colours, strict=True):
        tick_label.set_color(colour)

    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], color=theme.NEUTRAL, fontsize=8)
    ax.spines["polar"].set_color(theme.NEUTRAL)
    ax.grid(color=theme.NEUTRAL, alpha=0.3)

    fig.tight_layout()
    return fig


def _bar_chart(result: ScoreResult) -> Figure:
    """Draw every top-level subscale as an equal-width bar.

    Args:
        result: Computed scores for a single participant.

    Returns:
        The figure.
    """
    questionnaire = result.questionnaire
    top_level = questionnaire.subscales_at(questionnaire.levels[0])
    values = result.as_dict()
    names = [s.name for s in top_level]
    scores = [values[name] for name in names]

    scale = "[0, 1]" if result.normalized else f"[{questionnaire.minimum}, {questionnaire.maximum}]"
    palette = (theme.PRIMARY, theme.ACCENT, theme.SUCCESS, theme.DANGER, theme.NEUTRAL)
    colours = [palette[i % len(palette)] for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor(theme.PAPER)
    ax.set_facecolor(theme.PAPER)

    bars = ax.bar(names, scores, color=colours, width=0.5)
    ax.bar_label(bars, fmt="%.2f", color=theme.INK, fontsize=10)

    ax.set_ylabel(f"Score {scale}", color=theme.INK)
    ax.set_ylim(0, max(scores + [1.0]) * 1.15 if result.normalized else None)
    ax.tick_params(colors=theme.INK)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(theme.NEUTRAL)

    fig.tight_layout()
    return fig
