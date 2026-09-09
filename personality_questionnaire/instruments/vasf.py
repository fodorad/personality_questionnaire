"""The Visual Analogue Scale to Evaluate Fatigue Severity (VAS-F), 18 items.

Lee, K. A., Hicks, G., & Nino-Murcia, G. (1991). Validity and reliability of a scale
to assess fatigue. ``Psychiatry Research, 36(3)``, 291-298.

Each item is a line between two anchors, answered 0..10. Two of the three subscales
are the instrument's own, Fatigue and Energy, each scored in its own direction, and
the third is a derived composite offered for convenience and clearly labelled as
such.

The VAS-F is normally administered twice, before and after some intervention, and
its primary result is the difference. That makes it :attr:`~Questionnaire.paired`;
see :func:`personality_questionnaire.scoring.delta`.
"""

from __future__ import annotations

from personality_questionnaire.registry import (
    Item,
    Questionnaire,
    ScaleType,
    Subscale,
    register,
)

__all__ = ["VASF", "VASF_ITEM_TEXT"]

VASF_ITEM_TEXT: dict[int, str] = {
    1: "tired",
    2: "sleepy",
    3: "drowsy",
    4: "fatigued",
    5: "worn out",
    6: "energetic",
    7: "active",
    8: "vigorous",
    9: "efficient",
    10: "lively",
    11: "bushed",
    12: "exhausted",
    13: "keeping my eyes open",
    14: "moving my body",
    15: "concentrating",
    16: "carrying on a conversation",
    17: "desire to close my eyes",
    18: "desire to lie down",
}
"""The 18 VAS-F items, keyed by item number."""

_ANCHORS: dict[int, tuple[str, str]] = {
    1: ("not at all", "extremely"),
    2: ("not at all", "extremely"),
    3: ("not at all", "extremely"),
    4: ("not at all", "extremely"),
    5: ("not at all", "extremely"),
    6: ("not at all", "extremely"),
    7: ("not at all", "extremely"),
    8: ("not at all", "extremely"),
    9: ("not at all", "extremely"),
    10: ("not at all", "extremely"),
    11: ("not at all", "totally"),
    12: ("not at all", "totally"),
    13: ("is no effort at all", "is a tremendous chore"),
    14: ("is no effort at all", "is a tremendous chore"),
    15: ("is no effort at all", "is a tremendous chore"),
    16: ("is no effort at all", "is a tremendous chore"),
    17: ("I have absolutely no", "I have a tremendous"),
    18: ("I have absolutely no", "I have a tremendous"),
}
"""Per-item anchor pairs for the low and high ends of the 0..10 line."""

_EFFORT_ITEMS = frozenset({13, 14, 15, 16})
"""Items whose anchor follows the item text rather than preceding it.

"keeping my eyes open *is no effort at all*" reads correctly, where the adjective
items need "*not at all* tired". Encoding this here rather than at the call site is
what removes an index-range branch -- and a typo -- from the CLI.
"""


def _prompt(number: int, text: str, low: str, high: str) -> str:
    """Compose the participant-facing prompt for one item.

    Args:
        number: The item's number, used to pick the anchor word order.
        text: The item text.
        low: Anchor for 0.
        high: Anchor for 10.

    Returns:
        The fully-formed prompt.
    """
    if number in _EFFORT_ITEMS:
        return f'0 means "{text} {low}", 10 means "{text} {high}"'
    return f'0 means "{low} {text}", 10 means "{high} {text}"'


def _items() -> tuple[Item, ...]:
    """Build the item tuple with prompts already composed.

    Returns:
        The 18 items in administration order.
    """
    items = []
    for number, text in sorted(VASF_ITEM_TEXT.items()):
        low, high = _ANCHORS[number]
        items.append(
            Item(
                number=number,
                text=text,
                prompt=_prompt(number, text, low, high),
                low_anchor=low,
                high_anchor=high,
            )
        )
    return tuple(items)


_FATIGUE_ITEMS = (1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 16, 17, 18)
"""Items worded so that a high response indicates more fatigue."""

_ENERGY_ITEMS = (6, 7, 8, 9, 10)
"""Items worded so that a high response indicates more energy."""

VASF: Questionnaire = register(
    Questionnaire(
        key="vasf",
        name="Visual Analogue Scale to Evaluate Fatigue Severity",
        scale=ScaleType.VISUAL_ANALOGUE,
        minimum=0,
        maximum=10,
        items=_items(),
        subscales=(
            Subscale(
                name="Fatigue",
                items=_FATIGUE_ITEMS,
                level="subscale",
                higher_is="more fatigued",
            ),
            Subscale(
                name="Energy",
                items=_ENERGY_ITEMS,
                level="subscale",
                higher_is="more energetic",
            ),
            Subscale(
                name="Fatigue (composite)",
                items=tuple(range(1, 19)),
                reverse=frozenset(_ENERGY_ITEMS),
                level="composite",
                higher_is="more fatigued",
            ),
        ),
        citation=(
            "Lee, K. A., Hicks, G., & Nino-Murcia, G. (1991). Validity and "
            "reliability of a scale to assess fatigue. Psychiatry Research, "
            "36(3), 291-298."
        ),
        paired=True,
    )
)
"""The registered VAS-F instrument.

Fatigue and Energy are the instrument's own two scales, each scored in its own
direction. ``Fatigue (composite)`` reverse-keys the five energy items into the
fatigue direction to give a single number across all eighteen items; it is a
modelling convenience, not part of Lee et al.'s scoring, which is why it carries its
own ``"composite"`` level and an explicit name.
"""
