"""Formatting scores and instrument metadata for the terminal."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personality_questionnaire.registry import Questionnaire
    from personality_questionnaire.scoring import ScoreResult

__all__ = ["format_instrument", "format_registry", "format_scores"]


def format_scores(result: ScoreResult, row: int = 0, *, decimals: int = 3) -> list[str]:
    """Render one participant's scores, grouped by subscale level.

    Args:
        result: The computed scores.
        row: Index of the participant.
        decimals: Digits after the decimal point.

    Returns:
        Lines to print.
    """
    questionnaire = result.questionnaire
    scale = "[0..1]" if result.normalized else f"[{questionnaire.minimum}..{questionnaire.maximum}]"
    lines = [f"{questionnaire.name} scores {scale}:"]

    for level in questionnaire.levels:
        subscales = questionnaire.subscales_at(level)
        if not subscales:
            continue

        lines.append("")
        lines.append(f"  {level.title()}")
        width = max(len(s.name) for s in subscales)
        values = result.as_dict(row)
        for subscale in subscales:
            value = f"{values[subscale.name]:.{decimals}f}"
            direction = f"  (higher is {subscale.higher_is})" if subscale.higher_is else ""
            lines.append(f"    {subscale.name:<{width}}  {value}{direction}")

    return lines


def format_instrument(questionnaire: Questionnaire) -> list[str]:
    """Render an instrument's metadata and subscale tree.

    Args:
        questionnaire: The instrument to describe.

    Returns:
        Lines to print.
    """
    lines = [
        f"{questionnaire.name}  ({questionnaire.key})",
        "",
        f"  Items      {questionnaire.n_items}",
        f"  Scale      {questionnaire.scale.value} "
        f"[{questionnaire.minimum}..{questionnaire.maximum}]",
        f"  Paired     {'yes (pre/post)' if questionnaire.paired else 'no'}",
        "",
        "  Subscales",
    ]

    for level in questionnaire.levels:
        for subscale in questionnaire.subscales_at(level):
            reverse = f", {len(subscale.reverse)} reverse-keyed" if subscale.reverse else ""
            lines.append(f"    [{level}] {subscale.name} ({len(subscale.items)} items{reverse})")

    lines.extend(["", "  Citation", f"    {questionnaire.citation}"])
    if questionnaire.license_note:
        lines.extend(["", "  Licence", f"    {questionnaire.license_note}"])

    return lines


def format_registry(questionnaires: list[Questionnaire]) -> list[str]:
    """Render the instrument table.

    Args:
        questionnaires: Instruments to list.

    Returns:
        Lines to print.
    """
    if not questionnaires:
        return ["No instruments registered."]

    key_width = max(len(q.key) for q in questionnaires)
    name_width = max(len(q.name) for q in questionnaires)

    lines = [f"  {'KEY':<{key_width}}  {'NAME':<{name_width}}  ITEMS  SUBSCALES"]
    for questionnaire in questionnaires:
        lines.append(
            f"  {questionnaire.key:<{key_width}}  {questionnaire.name:<{name_width}}  "
            f"{questionnaire.n_items:>5}  {len(questionnaire.subscales):>9}"
        )
    return lines
