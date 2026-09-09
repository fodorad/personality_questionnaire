"""Central theme tokens -- every colour this project uses lives here.

Dark navy carries the chrome; a single burnt-orange accent marks the item
currently being answered. The pairing is deliberately far from the muted
teal-and-sage research-software look this project used before 2.5 -- close enough
to a sibling project's own petrol-and-ochre palette that the two applications were
hard to tell apart at a glance. Navy against warm paper, with orange as the one
saturated colour in the room, reads as its own thing.

Every foreground/background pairing defined here meets WCAG AA (4.5:1) for normal
text against :data:`PAPER` or white. ``tests/core/test_theme.py`` asserts it, so a
future colour tweak cannot quietly make the questionnaire harder to read.

Referenced by name, never as a raw hex literal at the call site, so a redesign
touches one file. The same tokens drive the documentation theme, the repository
icon and the localhost application.
"""

from __future__ import annotations

from typing import Literal

__all__ = [
    "ACCENT",
    "DANGER",
    "DOMAIN_COLORS",
    "INK",
    "LOGO_MARK_SVG",
    "NEUTRAL",
    "PAPER",
    "PRIMARY",
    "ROW_BORDER",
    "SUCCESS",
    "UNANSWERED",
    "WARNING",
    "color",
    "contrast_ratio",
    "domain_color",
]

PRIMARY = "#12294B"
"""Dark navy. Application header, primary actions, links."""

ACCENT = "#B84C14"
"""Burnt orange. The item being answered, progress fill -- the one saturated
colour in the palette, so it stays legible as a signal precisely because
everything else is quiet."""

SUCCESS = "#2E6E5E"
"""Deep teal-green. An item answered, a record saved."""

WARNING = "#8A5A00"
"""Dark amber. An incomplete record, unanswered items remaining."""

DANGER = "#A6303B"
"""Deep rust red. Validation failure, destructive actions."""

NEUTRAL = "#565F6E"
"""Cool slate. Secondary text, totals, disabled states."""

PAPER = "#FAF8F5"
"""Warm off-white. The page ground."""

INK = "#151B26"
"""Near-black with a navy cast. Body text."""

UNANSWERED = "#DDD8D0"
"""Same hairline colour as :data:`ROW_BORDER`, isolated for cases that need only
the colour rather than the full declaration -- an unanswered questionnaire item's
border, for instance."""

ROW_BORDER = f"1px solid {UNANSWERED}"
"""The hairline every list row and card carries."""

HEADER_FG = "#FFFFFF"
"""Header text and icons, readable on :data:`PRIMARY`."""

DOMAIN_COLORS: dict[str, str] = {
    "openness": "#3E4C8A",
    "conscientiousness": "#2E6E5E",
    "extraversion": "#B84C14",
    "agreeableness": "#7A4A82",
    "neuroticism": "#A6303B",
}
"""One colour per Big Five domain.

Shared by the application's chips and the analysis plots, so a domain keeps the same
colour wherever a reader meets it.
"""


def domain_color(subscale_name: str, parent: str | None) -> str:
    """Resolve a subscale's colour by the domain it belongs to.

    A domain-level subscale resolves through its own name. A facet resolves
    through ``parent`` -- its owning domain's name -- so it inherits the same
    colour as that domain rather than falling through to :data:`PRIMARY`, which is
    what a lookup keyed on the facet's own name would do (``DOMAIN_COLORS`` only
    has the five domain names as keys). Anything with no domain at all -- a PANAS
    scale, the VAS-F composite -- has no match either way and falls back to
    :data:`PRIMARY`, unchanged from before.

    Args:
        subscale_name: The subscale's own name.
        parent: The name of its owning domain, or ``None`` if it has none.

    Returns:
        The resolved colour.
    """
    return DOMAIN_COLORS.get((parent or subscale_name).lower(), PRIMARY)


ColorName = Literal["primary", "accent", "success", "warning", "danger", "neutral"]

_BY_NAME: dict[str, str] = {
    "primary": PRIMARY,
    "accent": ACCENT,
    "success": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
    "neutral": NEUTRAL,
}


def color(name: ColorName) -> str:
    """Look up a semantic colour by name.

    Args:
        name: One of the semantic role names.

    Returns:
        The hex value.

    Raises:
        KeyError: If the name is not a defined role.
    """
    try:
        return _BY_NAME[name]
    except KeyError:
        available = ", ".join(sorted(_BY_NAME))
        raise KeyError(f"unknown colour {name!r}; available: {available}") from None


def _relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance.

    Args:
        hex_color: A ``#rrggbb`` value.

    Returns:
        Luminance in ``[0, 1]``.
    """
    raw = hex_color.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Compute the WCAG contrast ratio between two colours.

    Args:
        foreground: A ``#rrggbb`` value.
        background: A ``#rrggbb`` value.

    Returns:
        The ratio, from 1.0 (identical) to 21.0 (black on white).
    """
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


LOGO_MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
    'style="width:100%;height:100%" role="img" aria-label="personality_questionnaire">'
    f'<g fill="{PRIMARY}" opacity="0.22">'
    '<circle cx="10" cy="10" r="3"/><circle cx="21" cy="10" r="3"/><circle cx="32" cy="10" r="3"/>'
    '<circle cx="43" cy="10" r="3"/><circle cx="54" cy="10" r="3"/>'
    '<circle cx="10" cy="22" r="3"/><circle cx="21" cy="22" r="3"/><circle cx="32" cy="22" r="3"/>'
    '<circle cx="43" cy="22" r="3"/><circle cx="54" cy="22" r="3"/>'
    '<circle cx="10" cy="34" r="3"/><circle cx="21" cy="34" r="3"/><circle cx="32" cy="34" r="3"/>'
    '<circle cx="43" cy="34" r="3"/><circle cx="54" cy="34" r="3"/>'
    '<circle cx="10" cy="46" r="3"/><circle cx="21" cy="46" r="3"/><circle cx="32" cy="46" r="3"/>'
    '<circle cx="43" cy="46" r="3"/><circle cx="54" cy="46" r="3"/>'
    '<circle cx="10" cy="58" r="3"/><circle cx="21" cy="58" r="3"/><circle cx="32" cy="58" r="3"/>'
    '<circle cx="43" cy="58" r="3"/><circle cx="54" cy="58" r="3"/>'
    "</g>"
    f'<g fill="{PRIMARY}">'
    '<circle cx="43" cy="10" r="5.6"/><circle cx="21" cy="22" r="5.6"/>'
    '<circle cx="54" cy="46" r="5.6"/><circle cx="32" cy="58" r="5.6"/>'
    "</g>"
    f'<circle cx="32" cy="34" r="6.8" fill="{ACCENT}"/>'
    "</svg>"
)
"""The repository mark: a five-by-five Likert response grid.

Five rows of five discrete options -- what a participant actually sees -- with the
filled marks tracing one person's answers and the ochre mark on the item being
answered. The rows double as the Big Five. Scales to its container, so the same
string serves the documentation header, the application header and the favicon, and
matches ``docs/assets/logo.svg`` exactly.
"""
