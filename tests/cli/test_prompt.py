"""Tests for the interactive item loop."""

from __future__ import annotations

import unittest

from personality_questionnaire import get
from personality_questionnaire.cli.prompt import ask_items, parse_response


class ScriptedParticipant:
    """A participant who types a fixed sequence of lines.

    Attributes:
        prompts: Every prompt they were shown, in order.
    """

    def __init__(self, lines: list[str]) -> None:
        """Store the script.

        Args:
            lines: Lines to type, in order.
        """
        self._lines = iter(lines)
        self.prompts: list[str] = []

    def read(self, prompt: str) -> str:
        """Answer one item.

        Args:
            prompt: The prompt shown.

        Returns:
            The next scripted line.
        """
        self.prompts.append(prompt)
        return next(self._lines)


class TestParseResponse(unittest.TestCase):
    """Response parsing accepts only in-range whole numbers."""

    def setUp(self):
        self.bfi2 = get("bfi2")

    def test_accepts_in_range(self):
        self.assertEqual(parse_response("4", self.bfi2), 4)

    def test_tolerates_surrounding_space(self):
        self.assertEqual(parse_response("  2  ", self.bfi2), 2)

    def test_rejects_out_of_range(self):
        self.assertIsNone(parse_response("0", self.bfi2))
        self.assertIsNone(parse_response("6", self.bfi2))

    def test_rejects_non_numeric(self):
        self.assertIsNone(parse_response("maybe", self.bfi2))

    def test_respects_a_zero_based_scale(self):
        self.assertEqual(parse_response("0", get("vasf")), 0)


class TestAskItems(unittest.TestCase):
    """The loop administers every item and handles quitting."""

    def test_collects_one_response_per_item(self):
        vasf = get("vasf")
        participant = ScriptedParticipant([str(i % 11) for i in range(vasf.n_items)])
        responses = ask_items(vasf, read=participant.read, write=lambda _: None)
        self.assertEqual(len(responses), vasf.n_items)

    def test_shows_every_item_prompt(self):
        vasf = get("vasf")
        participant = ScriptedParticipant(["5"] * vasf.n_items)
        ask_items(vasf, read=participant.read, write=lambda _: None)
        self.assertIn("not at all tired", participant.prompts[0])
        self.assertIn("keeping my eyes open", participant.prompts[12])

    def test_quitting_returns_none(self):
        participant = ScriptedParticipant(["quit"])
        self.assertIsNone(ask_items(get("bfi2"), read=participant.read, write=lambda _: None))

    def test_quit_is_case_insensitive(self):
        participant = ScriptedParticipant(["QUIT"])
        self.assertIsNone(ask_items(get("bfi2"), read=participant.read, write=lambda _: None))

    def test_end_of_input_raises_rather_than_returning_a_partial(self):
        """Running out of input is an error, not a quiet abandonment.

        Returning the answers collected so far would produce a partial record that
        scores as though the missing items had been answered.
        """

        def read(_: str) -> str:
            raise EOFError

        with self.assertRaisesRegex(EOFError, "item 1 of 60"):
            ask_items(get("bfi2"), read=read, write=lambda _: None)

    def test_end_of_input_names_the_item_reached(self):
        answers = iter(["3"] * 5)

        def read(_: str) -> str:
            try:
                return next(answers)
            except StopIteration:
                raise EOFError from None

        with self.assertRaisesRegex(EOFError, "item 6 of 60"):
            ask_items(get("bfi2"), read=read, write=lambda _: None)

    def test_reprompts_after_an_invalid_response(self):
        bfi2 = get("bfi2")
        participant = ScriptedParticipant(["99", "nope", *["3"] * bfi2.n_items])
        transcript: list[str] = []
        responses = ask_items(bfi2, read=participant.read, write=transcript.append)
        self.assertEqual(len(responses), bfi2.n_items)
        self.assertEqual(sum("whole number" in line for line in transcript), 2)

    def test_an_invalid_answer_does_not_consume_an_item(self):
        bfi2 = get("bfi2")
        participant = ScriptedParticipant(["0", *["2"] * bfi2.n_items])
        responses = ask_items(bfi2, read=participant.read, write=lambda _: None)
        self.assertTrue(all(value == 2 for value in responses))

    def test_legend_lists_the_labels(self):
        transcript: list[str] = []
        participant = ScriptedParticipant(["quit"])
        ask_items(get("bfi2"), read=participant.read, write=transcript.append)
        self.assertTrue(any("Disagree strongly" in line for line in transcript))


if __name__ == "__main__":
    unittest.main()
