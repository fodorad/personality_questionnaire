"""The Big Five Inventory-10 (BFI-10), 10 items.

Rammstedt, B., & John, O. P. (2007). Measuring personality in one minute or less: A
10-item short version of the Big Five Inventory in English and German. ``Journal of
Research in Personality, 41``, 203-212.

Two items per domain, one keyed in each direction, for settings under extreme time
pressure. Unlike the :mod:`~personality_questionnaire.instruments.bfi2_xs`, this form
is **not** a subset of the BFI-2: it descends from the older BFI-44, and its wording
differs. Its items are therefore native rather than borrowed, and carry no
``source_number``.

Domains only. With two items per domain there is no facet structure to score, and
the pairs are chosen for breadth rather than to represent any single facet.
"""

from __future__ import annotations

from personality_questionnaire.registry import (
    Item,
    Questionnaire,
    ScaleType,
    Subscale,
    register,
)

__all__ = ["BFI10", "BFI10_ITEM_TEXT", "BFI10_LABELS"]

BFI10_LABELS: dict[str, int] = {
    "Disagree strongly": 1,
    "Disagree a little": 2,
    "Neither agree nor disagree": 3,
    "Agree a little": 4,
    "Agree strongly": 5,
}
"""The BFI-10's five response options.

The midpoint is worded "Neither agree nor disagree", where the BFI-2 uses "Neutral;
no opinion". The labels are part of the published instrument, so they are not
harmonised across forms.
"""

_PREAMBLE = "I see myself as someone who..."
"""The stem every BFI-10 item completes.

The BFI-2 uses "I am someone who..."; both are reproduced as published.
"""

BFI10_ITEM_TEXT: dict[int, str] = {
    1: "is reserved",
    2: "is generally trusting",
    3: "tends to be lazy",
    4: "is relaxed, handles stress well",
    5: "has few artistic interests",
    6: "is outgoing, sociable",
    7: "tends to find fault with others",
    8: "does a thorough job",
    9: "gets nervous easily",
    10: "has an active imagination",
}
"""The 10 BFI-10 items, in the published administration order.

Transcribed from Appendix A of Rammstedt & John (2007). The items are lower-case and
unpunctuated in the source, completing the stem as a sentence.
"""

_DOMAIN_ITEMS: dict[str, tuple[tuple[int, ...], frozenset[int]]] = {
    "openness": ((5, 10), frozenset({5})),
    "conscientiousness": ((3, 8), frozenset({3})),
    "extraversion": ((1, 6), frozenset({1})),
    "agreeableness": ((2, 7), frozenset({7})),
    "neuroticism": ((4, 9), frozenset({4})),
}
"""Domain scales with their reverse keys, in the OCEAN order this package reports.

From the published key: ``Extraversion: 1R, 6; Agreeableness: 2, 7R;
Conscientiousness: 3R, 8; Neuroticism: 4R, 9; Openness: 5R, 10``. Each domain pairs
one positively and one negatively keyed item by design, which is why exactly five of
the ten items are reversed.
"""

_HIGHER_IS: dict[str, str] = {
    "openness": "more open to experience",
    "conscientiousness": "more conscientious",
    "extraversion": "more extraverted",
    "agreeableness": "more agreeable",
    "neuroticism": "more neurotic",
}
"""Scale direction, recorded so polarity is never inferred from a name."""


def _items() -> tuple[Item, ...]:
    """Build the item tuple, completing the shared stem.

    Returns:
        The 10 items in administration order.
    """
    return tuple(
        Item(
            number=number,
            text=text,
            prompt=f"{_PREAMBLE} {text}",
            low_anchor="Disagree strongly",
            high_anchor="Agree strongly",
        )
        for number, text in sorted(BFI10_ITEM_TEXT.items())
    )


BFI10: Questionnaire = register(
    Questionnaire(
        key="bfi10",
        name="Big Five Inventory-10",
        abbreviation="BFI-10",
        scale=ScaleType.LIKERT,
        minimum=1,
        maximum=5,
        items=_items(),
        subscales=tuple(
            Subscale(
                name=name,
                items=items,
                reverse=reverse,
                level="domain",
                higher_is=_HIGHER_IS[name],
            )
            for name, (items, reverse) in _DOMAIN_ITEMS.items()
        ),
        labels=BFI10_LABELS,
        citation=(
            "Rammstedt, B., & John, O. P. (2007). Measuring personality in one "
            "minute or less: A 10-item short version of the Big Five Inventory in "
            "English and German. Journal of Research in Personality, 41, 203-212."
        ),
        license_note="Free for research purposes.",
    )
)
"""The registered BFI-10 instrument."""
