"""The Positive and Negative Affect Schedule (PANAS), 20 items.

Watson, D., Clark, L. A., & Tellegen, A. (1988). Development and validation of brief
measures of positive and negative affect: the PANAS scales. ``Journal of Personality
and Social Psychology, 54(6)``, 1063-1070.

Twenty mood adjectives, ten measuring Positive Affect and ten Negative Affect, rated
for how strongly the respondent has felt that way over a stated period. The two
scales are near-independent rather than opposite ends of one dimension, which is the
instrument's central claim.

**No item is reverse-keyed.** Each adjective is scored in the direction it is worded,
and a negative adjective raises Negative Affect rather than lowering Positive Affect.
This makes the PANAS the first shipped instrument whose reverse-key set is empty,
which exercises that branch of the shared scorer.

Like the VAS-F, the PANAS is well suited to pre/post administration around an
intervention; see :func:`personality_questionnaire.scoring.delta`.
"""

from __future__ import annotations

from personality_questionnaire.registry import (
    Aggregation,
    Item,
    Questionnaire,
    ScaleType,
    Subscale,
    register,
)

__all__ = ["PANAS", "PANAS_ITEM_TEXT", "PANAS_LABELS"]

PANAS_LABELS: dict[str, int] = {
    "Very slightly or not at all": 1,
    "A little": 2,
    "Moderately": 3,
    "Quite a bit": 4,
    "Extremely": 5,
}
"""The PANAS's five response options.

These describe intensity rather than agreement, unlike the BFI forms: the respondent
reports how strongly a mood applied, not whether a statement is true of them.
"""

_PREAMBLE = "Indicate the extent you have felt this way over the past week:"
"""The stem, as printed on the published form.

The time frame is the instrument's one deliberate variable -- Watson et al. validate
"right now", "today", "the past few days", "the past week", "the past few weeks",
"the past year" and "in general", and the scale's test-retest behaviour changes with
it. The past week is the published default reproduced here; a study using another
window should say so in its own materials.
"""

PANAS_ITEM_TEXT: dict[int, str] = {
    1: "Interested",
    2: "Distressed",
    3: "Excited",
    4: "Upset",
    5: "Strong",
    6: "Guilty",
    7: "Scared",
    8: "Hostile",
    9: "Enthusiastic",
    10: "Proud",
    11: "Irritable",
    12: "Alert",
    13: "Ashamed",
    14: "Inspired",
    15: "Nervous",
    16: "Determined",
    17: "Attentive",
    18: "Jittery",
    19: "Active",
    20: "Afraid",
}
"""The 20 PANAS adjectives, in the published administration order.

Positive and negative adjectives alternate early in the form and interleave
throughout, so a respondent cannot answer a whole scale by pattern.
"""

_POSITIVE_ITEMS = (1, 3, 5, 9, 10, 12, 14, 16, 17, 19)
"""Items forming the Positive Affect scale, from the published scoring key."""

_NEGATIVE_ITEMS = (2, 4, 6, 7, 8, 11, 13, 15, 18, 20)
"""Items forming the Negative Affect scale, from the published scoring key."""


def _items() -> tuple[Item, ...]:
    """Build the item tuple.

    Each adjective is presented on its own; the stem is shown once, so the prompt is
    the adjective plus the intensity question rather than a full sentence.

    Returns:
        The 20 items in administration order.
    """
    return tuple(
        Item(
            number=number,
            text=text,
            prompt=f"{_PREAMBLE} {text}",
            low_anchor="Very slightly or not at all",
            high_anchor="Extremely",
        )
        for number, text in sorted(PANAS_ITEM_TEXT.items())
    )


PANAS: Questionnaire = register(
    Questionnaire(
        key="panas",
        name="Positive and Negative Affect Schedule",
        scale=ScaleType.LIKERT,
        minimum=1,
        maximum=5,
        items=_items(),
        subscales=(
            Subscale(
                name="Positive Affect",
                items=_POSITIVE_ITEMS,
                level="scale",
                higher_is="more positive affect",
            ),
            Subscale(
                name="Negative Affect",
                items=_NEGATIVE_ITEMS,
                level="scale",
                higher_is="more negative affect",
            ),
            Subscale(
                name="Positive Affect (sum)",
                items=_POSITIVE_ITEMS,
                level="published total",
                higher_is="more positive affect",
                aggregation=Aggregation.SUM,
            ),
            Subscale(
                name="Negative Affect (sum)",
                items=_NEGATIVE_ITEMS,
                level="published total",
                higher_is="more negative affect",
                aggregation=Aggregation.SUM,
            ),
        ),
        labels=PANAS_LABELS,
        citation=(
            "Watson, D., Clark, L. A., & Tellegen, A. (1988). Development and "
            "validation of brief measures of positive and negative affect: the "
            "PANAS scales. Journal of Personality and Social Psychology, 54(6), "
            "1063-1070."
        ),
        license_note="Free for research purposes.",
    )
)
"""The registered PANAS instrument.

Each scale is reported twice. ``Positive Affect`` and ``Negative Affect`` are means
normalised to ``[0, 1]``, matching every other instrument here so downstream code
sees one convention. ``Positive Affect (sum)`` and ``Negative Affect (sum)`` are the
10-50 totals the literature is written in -- Watson et al. report normative means of
33.3 for Positive Affect and 17.4 for Negative Affect -- so a published comparison
needs no arithmetic at the call site.
"""
