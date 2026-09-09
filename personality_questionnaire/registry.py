"""The instrument registry: what a questionnaire *is*, expressed as data.

Every shipped instrument is a :class:`Questionnaire` value built from
:class:`Item` and :class:`Subscale` values. There is deliberately no per-instrument
behaviour here and no subclassing: adding an instrument means adding data, and the
arithmetic lives once in :mod:`personality_questionnaire.scoring`.

Instrument definitions are Python literals rather than shipped data files. They are
checked by the type checker, validated at import by :meth:`Questionnaire.validate`,
and present in the wheel by construction -- a data file is checked by nothing until
a participant has already answered every item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "REGISTRY",
    "Aggregation",
    "Item",
    "Questionnaire",
    "ScaleType",
    "Subscale",
    "get",
    "keys",
    "register",
]


class Aggregation(StrEnum):
    """How a subscale combines its items into a score.

    Most instruments average, which keeps a score on the same range as a single
    item and makes scales of different lengths comparable. Some are published as a
    total instead -- the PANAS reports 10-50 per scale -- and reproducing the
    published number matters more than internal consistency there.
    """

    MEAN = "mean"
    """Average of the (reverse-keyed) items. Normalisable to ``[0, 1]``."""

    SUM = "sum"
    """Total of the (reverse-keyed) items, as published. Never normalised."""


class ScaleType(StrEnum):
    """How a single item is answered.

    The value drives widget selection in the UI and validation in the CLI; it never
    affects the arithmetic, which is parameterised by the response range instead.
    """

    LIKERT = "likert"
    """Discrete ordered categories with verbal labels, rendered as radio buttons."""

    VISUAL_ANALOGUE = "vas"
    """A continuous line between two anchors, rendered as a slider."""


@dataclass(frozen=True, slots=True)
class Item:
    """One questionnaire item.

    Attributes:
        number: Position in this instrument's own administration order, 1-based.
        text: The bare statement or adjective, without anchors or framing.
        prompt: The fully-formed question as shown to a participant, with any
            anchors already embedded. Callers display this verbatim; assembling
            prompt text at the call site is what let a typo and an index-range
            branch live in the CLI before 2.0.
        low_anchor: Label for the minimum of the response range.
        high_anchor: Label for the maximum of the response range.
        source_number: Item number in the parent instrument when this item is
            borrowed rather than native. ``None`` for a native item. The BFI-2-XS
            borrows all fifteen of its items from the BFI-2; the BFI-10 borrows
            none, because its wording descends from the BFI-44 instead.
    """

    number: int
    text: str
    prompt: str
    low_anchor: str
    high_anchor: str
    source_number: int | None = None


@dataclass(frozen=True, slots=True)
class Subscale:
    """A scored scale: a set of items, some of which may be reverse-keyed.

    Hierarchy is recorded but never computed with. The BFI-2 declares its five
    domains and its fifteen facets as siblings, each listing the item numbers it
    covers directly, so both levels are scored in a single pass. ``parent`` exists
    to draw the tree in the UI and the docs, not to compose one scale from another.

    Attributes:
        name: Display name, e.g. ``"Anxiety"`` or ``"Positive Affect"``.
        items: Item numbers contributing to this scale, in this instrument's own
            1-based numbering.
        reverse: The subset of ``items`` that are reverse-keyed.
        level: Grouping tag -- ``"domain"``, ``"facet"`` or ``"subscale"``. Used for
            output ordering and UI grouping only.
        parent: Name of the enclosing subscale, when there is one.
        higher_is: Plain-language direction of the scale, e.g. ``"more neurotic"``.
            Recorded as data so a consumer never has to infer polarity from a name,
            which is precisely the inference that went wrong before 2.0.
        aggregation: How the items combine. Defaults to a mean; a scale published as
            a total declares :attr:`Aggregation.SUM`, and is left unnormalised so it
            reproduces the published number.
    """

    name: str
    items: tuple[int, ...]
    reverse: frozenset[int] = frozenset()
    level: str = "subscale"
    parent: str | None = None
    higher_is: str = ""
    aggregation: Aggregation = Aggregation.MEAN


@dataclass(frozen=True, slots=True)
class Questionnaire:
    """A complete, self-describing instrument.

    Attributes:
        key: Registry key and CLI token, e.g. ``"bfi2"`` or ``"bfi2-xs"``.
        name: Full human-readable name.
        abbreviation: The instrument's conventional short form, as printed in the
            literature, e.g. ``"BFI-2-XS"`` or ``"VAS-F"``. Distinct from ``key``,
            which is the lowercase registry/CLI token -- the mapping between them
            isn't mechanical (``vasf`` is ``"VAS-F"``, not ``"VASF"``), so this is
            supplied per instrument rather than derived.
        scale: How items are answered.
        minimum: Lowest valid response value.
        maximum: Highest valid response value.
        items: The items, in administration order.
        subscales: Every scored scale, in output order.
        citation: Full citation of the source publication.
        labels: Ordered response labels mapped to their values, for a Likert scale.
            Empty for a visual-analogue scale, whose ends are described by each
            item's own anchors.
        license_note: Any use restriction the publisher attaches.
        paired: Whether the instrument is administered twice and its primary result
            is a pre/post difference, as the VAS-F is.
        normalize: Whether :func:`~personality_questionnaire.scoring.score` rescales
            subscale means to ``[0, 1]`` by default.
    """

    key: str
    name: str
    abbreviation: str
    scale: ScaleType
    minimum: int
    maximum: int
    items: tuple[Item, ...]
    subscales: tuple[Subscale, ...]
    citation: str
    labels: dict[str, int] = field(default_factory=dict)
    license_note: str = ""
    paired: bool = False
    normalize: bool = True

    @property
    def n_items(self) -> int:
        """The number of items in the instrument."""
        return len(self.items)

    @property
    def item_numbers(self) -> frozenset[int]:
        """Every valid item number."""
        return frozenset(item.number for item in self.items)

    def item(self, number: int) -> Item:
        """Return the item with the given number.

        Args:
            number: The item's 1-based number.

        Returns:
            The matching item.

        Raises:
            KeyError: If no item carries that number.
        """
        for item in self.items:
            if item.number == number:
                return item
        raise KeyError(f"{self.key} has no item {number}; valid: 1..{self.n_items}")

    def subscale(self, name: str) -> Subscale:
        """Return the subscale with the given name.

        Args:
            name: The subscale's display name.

        Returns:
            The matching subscale.

        Raises:
            KeyError: If no subscale carries that name.
        """
        for subscale in self.subscales:
            if subscale.name == name:
                return subscale
        available = ", ".join(s.name for s in self.subscales)
        raise KeyError(f"{self.key} has no subscale {name!r}; available: {available}")

    def subscales_at(self, level: str) -> tuple[Subscale, ...]:
        """Return every subscale tagged with the given level.

        Args:
            level: One of ``"domain"``, ``"facet"`` or ``"subscale"``.

        Returns:
            The matching subscales, in declaration order.
        """
        return tuple(s for s in self.subscales if s.level == level)

    @property
    def levels(self) -> tuple[str, ...]:
        """The distinct subscale levels, in first-appearance order."""
        seen: dict[str, None] = {}
        for subscale in self.subscales:
            seen.setdefault(subscale.level, None)
        return tuple(seen)

    def validate(self) -> None:
        """Check the instrument's internal consistency.

        Called by :func:`register`, so a malformed instrument fails at import time
        -- and therefore in CI -- rather than producing a plausible wrong score.

        Raises:
            ValueError: If item numbering is not ``1..n``, if a subscale references
                an unknown item, if a reverse key is not among its own subscale's
                items, if an item belongs to no subscale, if a subscale name is
                duplicated, if a declared parent does not exist, if the response
                range is empty, or if the abbreviation is blank.
        """
        if not self.abbreviation.strip():
            raise ValueError(f"{self.key}: abbreviation must not be blank")

        if self.minimum >= self.maximum:
            raise ValueError(
                f"{self.key}: response range is empty "
                f"(minimum={self.minimum}, maximum={self.maximum})"
            )

        expected = tuple(range(1, self.n_items + 1))
        actual = tuple(item.number for item in self.items)
        if actual != expected:
            raise ValueError(
                f"{self.key}: items must be numbered 1..{self.n_items} in order, got {actual}"
            )

        names = [s.name for s in self.subscales]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"{self.key}: duplicate subscale names {sorted(duplicates)}")

        valid = self.item_numbers
        covered: set[int] = set()
        for subscale in self.subscales:
            if not subscale.items:
                raise ValueError(f"{self.key}: subscale {subscale.name!r} has no items")

            unknown = set(subscale.items) - valid
            if unknown:
                raise ValueError(
                    f"{self.key}: subscale {subscale.name!r} references "
                    f"unknown items {sorted(unknown)}"
                )

            orphan_reverse = subscale.reverse - set(subscale.items)
            if orphan_reverse:
                raise ValueError(
                    f"{self.key}: subscale {subscale.name!r} reverse-keys "
                    f"{sorted(orphan_reverse)}, which it does not contain"
                )

            if subscale.parent is not None and subscale.parent not in names:
                raise ValueError(
                    f"{self.key}: subscale {subscale.name!r} names a missing "
                    f"parent {subscale.parent!r}"
                )

            covered.update(subscale.items)

        unreachable = valid - covered
        if unreachable:
            raise ValueError(
                f"{self.key}: items {sorted(unreachable)} belong to no subscale "
                "and would be collected but never scored"
            )

        if self.scale is ScaleType.LIKERT and not self.labels:
            raise ValueError(f"{self.key}: a Likert instrument must define response labels")

        if self.labels:
            expected_values = set(range(self.minimum, self.maximum + 1))
            if set(self.labels.values()) != expected_values:
                raise ValueError(
                    f"{self.key}: response labels must cover {self.minimum}..{self.maximum} exactly"
                )


REGISTRY: dict[str, Questionnaire] = {}
"""Every registered instrument, keyed by :attr:`Questionnaire.key`.

Populated at import of :mod:`personality_questionnaire.instruments`. Treat as
read-only; use :func:`register` to add to it.
"""


def register(questionnaire: Questionnaire) -> Questionnaire:
    """Validate an instrument and add it to the registry.

    Args:
        questionnaire: The instrument to register.

    Returns:
        The same instrument, so a module can both register and export it in one
        statement.

    Raises:
        ValueError: If the key is already registered, or the instrument fails
            :meth:`Questionnaire.validate`.
    """
    if questionnaire.key in REGISTRY:
        raise ValueError(f"instrument {questionnaire.key!r} is already registered")

    questionnaire.validate()
    REGISTRY[questionnaire.key] = questionnaire
    return questionnaire


def get(key: str) -> Questionnaire:
    """Look up an instrument by key.

    Args:
        key: The registry key, e.g. ``"bfi2"``.

    Returns:
        The matching instrument.

    Raises:
        KeyError: If the key is not registered. The message lists what is.
    """
    try:
        return REGISTRY[key]
    except KeyError:
        available = ", ".join(sorted(REGISTRY)) or "(none registered)"
        raise KeyError(f"unknown instrument {key!r}; available: {available}") from None


def keys() -> tuple[str, ...]:
    """Return every registered key, sorted.

    Returns:
        The registry keys, suitable for an argparse ``choices``.
    """
    return tuple(sorted(REGISTRY))
