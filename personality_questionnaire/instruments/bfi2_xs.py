"""The BFI-2 Extra-Short Form (BFI-2-XS), 15 items.

Soto, C. J., & John, O. P. (2017). Short and extra-short forms of the Big Five
Inventory-2: The BFI-2-S and BFI-2-XS. ``Journal of Research in Personality, 68``,
69-81.

Three items per domain, one drawn from each of that domain's facets, retaining
roughly 80% of the full BFI-2's reliability at the domain level. Domains only: with
a single item per facet the form cannot support facet scores, and the authors say so
explicitly.

Every item is **borrowed from the BFI-2 by reference** rather than retyped, so a
wording correction in the parent propagates here and cannot silently diverge. Only
the mapping below is local to this module; ``tests/instruments/test_bfi2_xs.py``
asserts the borrowed text still matches its source.
"""

from __future__ import annotations

from dataclasses import replace

from personality_questionnaire.instruments.bfi2 import BFI2, BFI2_LABELS
from personality_questionnaire.registry import Questionnaire, ScaleType, Subscale, register

__all__ = ["BFI2_XS", "XS_TO_BFI2"]

XS_TO_BFI2: dict[int, int] = {
    1: 16,
    2: 2,
    3: 3,
    4: 34,
    5: 20,
    6: 21,
    7: 37,
    8: 23,
    9: 54,
    10: 55,
    11: 41,
    12: 57,
    13: 43,
    14: 29,
    15: 60,
}
"""BFI-2-XS item number to its BFI-2 source item number.

Taken from the published BFI-2-XS form, whose fifteen statements are a subset of the
BFI-2's sixty. The order is the form's own administration order, which is not the
parent's -- item 1 of the BFI-2-XS is item 16 of the BFI-2.
"""

_DOMAIN_ITEMS: dict[str, tuple[int, ...]] = {
    "openness": (5, 10, 15),
    "conscientiousness": (3, 8, 13),
    "extraversion": (1, 6, 11),
    "agreeableness": (2, 7, 12),
    "neuroticism": (4, 9, 14),
}
"""Domain scales in BFI-2-XS numbering, in the OCEAN order this package reports.

The published key lists these as Extraversion ``1R, 6, 11``; Agreeableness ``2, 7R,
12``; Conscientiousness ``3R, 8R, 13``; Negative Emotionality ``4, 9, 14R``;
Open-Mindedness ``5, 10R, 15``. Reverse keys are derived from the parent rather than
transcribed -- see :func:`_reverse_for`.
"""

_HIGHER_IS: dict[str, str] = {
    "openness": "more open-minded",
    "conscientiousness": "more conscientious",
    "extraversion": "more extraverted",
    "agreeableness": "more agreeable",
    "neuroticism": "more neurotic",
}
"""Scale direction, matching the parent instrument's."""


def _reverse_for(items: tuple[int, ...]) -> frozenset[int]:
    """Derive which of these items are reverse-keyed, from the BFI-2 itself.

    An item's polarity is a property of its wording, so a borrowed item keeps the
    keying its source carries. Deriving it removes the chance of transcribing the
    published key wrongly, and a test checks the result against that key anyway.

    Args:
        items: Item numbers in BFI-2-XS numbering.

    Returns:
        The subset that is reverse-keyed.
    """
    parent_reverse = {n for subscale in BFI2.subscales_at("domain") for n in subscale.reverse}
    return frozenset(n for n in items if XS_TO_BFI2[n] in parent_reverse)


def _items() -> tuple:
    """Borrow the fifteen items from the BFI-2, renumbered for this form.

    Returns:
        The items in BFI-2-XS administration order, each carrying the parent item
        number it came from.
    """
    return tuple(
        replace(BFI2.item(source), number=number, source_number=source)
        for number, source in sorted(XS_TO_BFI2.items())
    )


BFI2_XS: Questionnaire = register(
    Questionnaire(
        key="bfi2-xs",
        name="Big Five Inventory-2 Extra-Short Form",
        scale=ScaleType.LIKERT,
        minimum=BFI2.minimum,
        maximum=BFI2.maximum,
        items=_items(),
        subscales=tuple(
            Subscale(
                name=name,
                items=items,
                reverse=_reverse_for(items),
                level="domain",
                higher_is=_HIGHER_IS[name],
            )
            for name, items in _DOMAIN_ITEMS.items()
        ),
        labels=BFI2_LABELS,
        citation=(
            "Soto, C. J., & John, O. P. (2017). Short and extra-short forms of the "
            "Big Five Inventory-2: The BFI-2-S and BFI-2-XS. Journal of Research in "
            "Personality, 68, 69-81."
        ),
        license_note=BFI2.license_note,
    )
)
"""The registered BFI-2-XS instrument.

Domains only. The form carries one item per facet, which is too few to estimate a
facet score, so no facet subscales are declared.
"""
