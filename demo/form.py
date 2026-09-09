"""Pure logic for turning an instrument into form fields and back into responses.

Kept free of any Gradio import so it can be unit-tested directly: a widget
descriptor here says what to render and how, not how to render it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from personality_questionnaire.registry import ScaleType

if TYPE_CHECKING:
    from personality_questionnaire.registry import Item, Questionnaire

__all__ = ["MAX_ITEMS", "FieldSpec", "missing_items", "field_specs"]

MAX_ITEMS = 60
"""The largest item count across every registered instrument (BFI-2).

The demo pre-builds this many form rows once and toggles their visibility per
instrument, rather than rebuilding the Gradio graph per selection.
"""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """What to render for one item, independent of any UI toolkit.

    Attributes:
        item: The item this field answers.
        kind: ``"radio"`` for a Likert item, ``"slider"`` for a visual-analogue one.
        choices: Ordered ``(label, value)`` pairs, for a radio field. Empty for a
            slider.
        minimum: Slider lower bound. ``0`` for a radio field.
        maximum: Slider upper bound. ``0`` for a radio field.
    """

    item: Item
    kind: str
    choices: tuple[tuple[str, int], ...]
    minimum: int
    maximum: int


def field_specs(questionnaire: Questionnaire) -> tuple[FieldSpec, ...]:
    """Describe one form field per item of an instrument.

    Args:
        questionnaire: The instrument to build a form for.

    Returns:
        One :class:`FieldSpec` per item, in administration order.
    """
    if questionnaire.scale is ScaleType.LIKERT:
        choices = tuple(questionnaire.labels.items())
        return tuple(
            FieldSpec(item=item, kind="radio", choices=choices, minimum=0, maximum=0)
            for item in questionnaire.items
        )
    return tuple(
        FieldSpec(
            item=item,
            kind="slider",
            choices=(),
            minimum=questionnaire.minimum,
            maximum=questionnaire.maximum,
        )
        for item in questionnaire.items
    )


def missing_items(questionnaire: Questionnaire, responses: dict[int, int]) -> tuple[int, ...]:
    """Report which items of an instrument have no response yet.

    Args:
        questionnaire: The instrument being answered.
        responses: Item number to response value, for whatever has been answered.

    Returns:
        Unanswered item numbers, in administration order.
    """
    return tuple(item.number for item in questionnaire.items if item.number not in responses)
