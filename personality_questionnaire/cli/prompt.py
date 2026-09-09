"""The interactive item loop.

Reading and writing are injected rather than called directly, so the whole
administration path is unit-testable with a scripted participant and a captured
transcript. That matters because this is the one code path a participant actually
touches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from personality_questionnaire.registry import Questionnaire

__all__ = ["QUIT_WORDS", "ask_items", "parse_response"]

QUIT_WORDS = frozenset({"quit", "exit", "q"})
"""Words that abandon the questionnaire instead of answering an item."""


def parse_response(raw: str, questionnaire: Questionnaire) -> int | None:
    """Parse one typed response.

    Args:
        raw: What the participant typed.
        questionnaire: The instrument being administered.

    Returns:
        The parsed value, or ``None`` if it was not a valid response.
    """
    try:
        value = int(raw.strip())
    except ValueError:
        return None

    if not questionnaire.minimum <= value <= questionnaire.maximum:
        return None

    return value


def _legend(questionnaire: Questionnaire) -> list[str]:
    """Build the response-scale legend shown before the first item.

    Args:
        questionnaire: The instrument being administered.

    Returns:
        Lines to print.
    """
    if questionnaire.labels:
        ordered = sorted(questionnaire.labels.items(), key=lambda pair: pair[1])
        return [f"  {value}: {label}" for label, value in ordered]

    return [
        f"  Answer each item from {questionnaire.minimum} to {questionnaire.maximum}.",
        "  Each item names what its two extremes mean.",
    ]


def ask_items(
    questionnaire: Questionnaire,
    *,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> list[int] | None:
    """Administer every item of an instrument.

    Input may come from a terminal or from a pipe -- piping answers in is a
    legitimate way to script an administration. What is *not* legitimate is input
    running out mid-questionnaire: that yields a partial record, so it raises rather
    than returning whatever was collected so far.

    Args:
        questionnaire: The instrument to administer.
        read: Called with a prompt, returns the participant's line.
        write: Called with each line of output.

    Returns:
        One response per item in administration order, or ``None`` if the
        participant quit.

    Raises:
        EOFError: If input ends before every item is answered.
    """
    write(f"{questionnaire.name} ({questionnaire.n_items} items)")
    write("")
    write("Response scale:")
    for line in _legend(questionnaire):
        write(line)
    write("")
    write('Type "quit" at any point to stop without saving.')
    write("")

    responses: list[int] = []
    for item in questionnaire.items:
        while True:
            try:
                raw = read(f"Q{item.number}/{questionnaire.n_items}: {item.prompt}\n> ")
            except EOFError:
                raise EOFError(
                    f"input ended at item {item.number} of {questionnaire.n_items}; "
                    "a partial questionnaire cannot be scored"
                ) from None

            if raw.strip().lower() in QUIT_WORDS:
                return None

            value = parse_response(raw, questionnaire)
            if value is None:
                write(
                    f"  Please enter a whole number from {questionnaire.minimum} "
                    f'to {questionnaire.maximum}, or "quit".'
                )
                continue

            responses.append(value)
            break

    return responses
