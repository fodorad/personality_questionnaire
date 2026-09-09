"""The Big Five Inventory-2 (BFI-2), 60 items.

Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2): Developing
and assessing a hierarchical model with 15 facets to enhance bandwidth, fidelity,
and predictive power. ``Journal of Personality and Social Psychology, 113``, 117-143.

The BFI-2 is hierarchical: five domains, each resolved by three facets of four items.
Both levels are declared here as sibling subscales over the item pool rather than
composing domains from facets, because the arithmetic is identical either way and
flat declaration lets a single matrix multiplication produce every score at once.

.. note::
   The three Negative Emotionality facets are scored in the direction their names
   describe -- higher means more anxious, more depressed, more volatile. Before 2.0
   they were flipped unconditionally while the domain was not, so ``OCEAN`` and
   ``FACET`` disagreed on polarity by default. See
   :func:`personality_questionnaire.bfi2.bfi2` for the compatibility switch.
"""

from __future__ import annotations

from personality_questionnaire.registry import (
    Item,
    Questionnaire,
    ScaleType,
    Subscale,
    register,
)

__all__ = ["BFI2", "BFI2_ITEM_TEXT", "BFI2_LABELS"]

BFI2_LABELS: dict[str, int] = {
    "Disagree strongly": 1,
    "Disagree a little": 2,
    "Neutral; no opinion": 3,
    "Agree a little": 4,
    "Agree strongly": 5,
}
"""The BFI-2's five response options, in ascending order."""

_PREAMBLE = "I am someone who..."
"""The stem every BFI-2 item completes."""

BFI2_ITEM_TEXT: dict[int, str] = {
    1: "Is outgoing, sociable.",
    2: "Is compassionate, has a soft heart.",
    3: "Tends to be disorganized.",
    4: "Is relaxed, handles stress well.",
    5: "Has few artistic interests.",
    6: "Has an assertive personality.",
    7: "Is respectful, treats others with respect.",
    8: "Tends to be lazy.",
    9: "Stays optimistic after experiencing a setback.",
    10: "Is curious about many different things.",
    11: "Rarely feels excited or eager.",
    12: "Tends to find fault with others.",
    13: "Is dependable, steady.",
    14: "Is moody, has up and down mood swings.",
    15: "Is inventive, finds clever ways to do things.",
    16: "Tends to be quiet.",
    17: "Feels little sympathy for others.",
    18: "Is systematic, likes to keep things in order.",
    19: "Can be tense.",
    20: "Is fascinated by art, music, or literature.",
    21: "Is dominant, acts as a leader.",
    22: "Starts arguments with others.",
    23: "Has difficulty getting started on tasks.",
    24: "Feels secure, comfortable with self.",
    25: "Avoids intellectual, philosophical discussions.",
    26: "Is less active than other people.",
    27: "Has a forgiving nature.",
    28: "Can be somewhat careless.",
    29: "Is emotionally stable, not easily upset.",
    30: "Has little creativity.",
    31: "Is sometimes shy, introverted.",
    32: "Is helpful and unselfish with others.",
    33: "Keeps things neat and tidy.",
    34: "Worries a lot.",
    35: "Values art and beauty.",
    36: "Finds it hard to influence people.",
    37: "Is sometimes rude to others.",
    38: "Is efficient, gets things done.",
    39: "Often feels sad.",
    40: "Is complex, a deep thinker.",
    41: "Is full of energy.",
    42: "Is suspicious of others' intentions.",
    43: "Is reliable, can always be counted on.",
    44: "Keeps their emotions under control.",
    45: "Has difficulty imagining things.",
    46: "Is talkative.",
    47: "Can be cold and uncaring.",
    48: "Leaves a mess, doesn't clean up.",
    49: "Rarely feels anxious or afraid.",
    50: "Thinks poetry and plays are boring.",
    51: "Prefers to have others take charge.",
    52: "Is polite, courteous to others.",
    53: "Is persistent, works until the task is finished.",
    54: "Tends to feel depressed, blue.",
    55: "Has little interest in abstract ideas.",
    56: "Shows a lot of enthusiasm.",
    57: "Assumes the best about people.",
    58: "Sometimes behaves irresponsibly.",
    59: "Is temperamental, gets emotional easily.",
    60: "Is original, comes up with new ideas.",
}
"""The 60 BFI-2 items, keyed by item number.

Exposed because the short forms borrow from this pool by reference and the shipped
TSV is generated from it.
"""


def _items() -> tuple[Item, ...]:
    """Build the item tuple, giving every item the shared stem as its prompt.

    Returns:
        The 60 items in administration order.
    """
    return tuple(
        Item(
            number=number,
            text=text,
            prompt=f"{_PREAMBLE} {text}",
            low_anchor="Disagree strongly",
            high_anchor="Agree strongly",
        )
        for number, text in sorted(BFI2_ITEM_TEXT.items())
    )


_FACETS: tuple[Subscale, ...] = (
    Subscale(
        name="Sociability",
        items=(1, 16, 31, 46),
        reverse=frozenset({16, 31}),
        level="facet",
        parent="extraversion",
        higher_is="more sociable",
    ),
    Subscale(
        name="Assertiveness",
        items=(6, 21, 36, 51),
        reverse=frozenset({36, 51}),
        level="facet",
        parent="extraversion",
        higher_is="more assertive",
    ),
    Subscale(
        name="Energy Level",
        items=(11, 26, 41, 56),
        reverse=frozenset({11, 26}),
        level="facet",
        parent="extraversion",
        higher_is="more energetic",
    ),
    Subscale(
        name="Compassion",
        items=(2, 17, 32, 47),
        reverse=frozenset({17, 47}),
        level="facet",
        parent="agreeableness",
        higher_is="more compassionate",
    ),
    Subscale(
        name="Respectfulness",
        items=(7, 22, 37, 52),
        reverse=frozenset({22, 37}),
        level="facet",
        parent="agreeableness",
        higher_is="more respectful",
    ),
    Subscale(
        name="Trust",
        items=(12, 27, 42, 57),
        reverse=frozenset({12, 42}),
        level="facet",
        parent="agreeableness",
        higher_is="more trusting",
    ),
    Subscale(
        name="Organization",
        items=(3, 18, 33, 48),
        reverse=frozenset({3, 48}),
        level="facet",
        parent="conscientiousness",
        higher_is="more organized",
    ),
    Subscale(
        name="Productiveness",
        items=(8, 23, 38, 53),
        reverse=frozenset({8, 23}),
        level="facet",
        parent="conscientiousness",
        higher_is="more productive",
    ),
    Subscale(
        name="Responsibility",
        items=(13, 28, 43, 58),
        reverse=frozenset({28, 58}),
        level="facet",
        parent="conscientiousness",
        higher_is="more responsible",
    ),
    Subscale(
        name="Anxiety",
        items=(4, 19, 34, 49),
        reverse=frozenset({4, 49}),
        level="facet",
        parent="neuroticism",
        higher_is="more anxious",
    ),
    Subscale(
        name="Depression",
        items=(9, 24, 39, 54),
        reverse=frozenset({9, 24}),
        level="facet",
        parent="neuroticism",
        higher_is="more depressed",
    ),
    Subscale(
        name="Emotional Volatility",
        items=(14, 29, 44, 59),
        reverse=frozenset({29, 44}),
        level="facet",
        parent="neuroticism",
        higher_is="more emotionally volatile",
    ),
    Subscale(
        name="Intellectual Curiosity",
        items=(10, 25, 40, 55),
        reverse=frozenset({25, 55}),
        level="facet",
        parent="openness",
        higher_is="more intellectually curious",
    ),
    Subscale(
        name="Aesthetic Sensitivity",
        items=(5, 20, 35, 50),
        reverse=frozenset({5, 50}),
        level="facet",
        parent="openness",
        higher_is="more aesthetically sensitive",
    ),
    Subscale(
        name="Creative Imagination",
        items=(15, 30, 45, 60),
        reverse=frozenset({30, 45}),
        level="facet",
        parent="openness",
        higher_is="more creatively imaginative",
    ),
)
"""The fifteen BFI-2 facets, three per domain, four items each."""

_DOMAINS: tuple[Subscale, ...] = (
    Subscale(
        name="openness",
        items=(5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60),
        reverse=frozenset({5, 25, 30, 45, 50, 55}),
        level="domain",
        higher_is="more open-minded",
    ),
    Subscale(
        name="conscientiousness",
        items=(3, 8, 13, 18, 23, 28, 33, 38, 43, 48, 53, 58),
        reverse=frozenset({3, 8, 23, 28, 48, 58}),
        level="domain",
        higher_is="more conscientious",
    ),
    Subscale(
        name="extraversion",
        items=(1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56),
        reverse=frozenset({11, 16, 26, 31, 36, 51}),
        level="domain",
        higher_is="more extraverted",
    ),
    Subscale(
        name="agreeableness",
        items=(2, 7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57),
        reverse=frozenset({12, 17, 22, 37, 42, 47}),
        level="domain",
        higher_is="more agreeable",
    ),
    Subscale(
        name="neuroticism",
        items=(4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59),
        reverse=frozenset({4, 9, 24, 29, 44, 49}),
        level="domain",
        higher_is="more neurotic",
    ),
)
"""The five BFI-2 domains.

Declared in ``openness, conscientiousness, extraversion, agreeableness,
neuroticism`` order -- the OCEAN order the pre-2.0 API returned, and the order
PersonalityLinMulT expects, so an exported record drops straight into a
self-report-versus-perception comparison.
"""

BFI2: Questionnaire = register(
    Questionnaire(
        key="bfi2",
        name="Big Five Inventory-2",
        scale=ScaleType.LIKERT,
        minimum=1,
        maximum=5,
        items=_items(),
        subscales=_DOMAINS + _FACETS,
        labels=BFI2_LABELS,
        citation=(
            "Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2): "
            "Developing and assessing a hierarchical model with 15 facets to enhance "
            "bandwidth, fidelity, and predictive power. Journal of Personality and "
            "Social Psychology, 113, 117-143."
        ),
        license_note=(
            "Free for research purposes. See "
            "https://www.colby.edu/psych/personality-lab/ for the authors' terms."
        ),
    )
)
"""The registered BFI-2 instrument."""
