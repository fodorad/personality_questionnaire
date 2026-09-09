"""Tests for the command-line entry point."""

from __future__ import annotations

import contextlib
import io as stdio
import json
import tempfile
import unittest
from pathlib import Path

from personality_questionnaire import registry
from personality_questionnaire.cli.main import EXIT_MISSING_INPUT, EXIT_OK, main
from tests.fixtures import FIXTURE_DIR


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Invoke the CLI and capture both streams.

    Args:
        argv: Arguments after the program name.

    Returns:
        The exit code, stdout and stderr.
    """
    out, err = stdio.StringIO(), stdio.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestList(unittest.TestCase):
    """``pq list`` enumerates the registry."""

    def test_lists_every_instrument(self):
        code, out, _ = run_cli(["list"])
        self.assertEqual(code, EXIT_OK)
        for key in registry.keys():
            with self.subTest(instrument=key):
                self.assertIn(key, out)

    def test_json_output_is_machine_readable(self):
        """Derived from the registry, so adding an instrument does not break this."""
        code, out, _ = run_cli(["list", "--json"])
        self.assertEqual(code, EXIT_OK)
        payload = json.loads(out)
        keys = {entry["key"] for entry in payload}
        self.assertEqual(keys, set(registry.keys()))
        self.assertEqual(next(e for e in payload if e["key"] == "bfi2")["items"], 60)

    def test_json_reports_each_instrument_faithfully(self):
        _, out, _ = run_cli(["list", "--json"])
        for entry in json.loads(out):
            instrument = registry.get(entry["key"])
            with self.subTest(instrument=entry["key"]):
                self.assertEqual(entry["items"], instrument.n_items)
                self.assertEqual(entry["subscales"], [s.name for s in instrument.subscales])


class TestInfo(unittest.TestCase):
    """``pq info`` describes one instrument."""

    def test_describes_subscales_and_citation(self):
        code, out, _ = run_cli(["info", "bfi2"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Soto", out)
        self.assertIn("Anxiety", out)

    def test_rejects_an_unknown_instrument(self):
        with self.assertRaises(SystemExit) as caught:
            run_cli(["info", "nope"])
        self.assertEqual(caught.exception.code, 2)


class TestScore(unittest.TestCase):
    """``pq score`` scores responses held in a file."""

    def test_scores_a_csv(self):
        code, out, _ = run_cli(
            ["score", "bfi2", "--input", str(FIXTURE_DIR / "test_bfi2_answers_int.csv")]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("openness", out)

    def test_scores_an_npy(self):
        code, out, _ = run_cli(
            ["score", "bfi2", "--input", str(FIXTURE_DIR / "test_bfi2_answers.npy")]
        )
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Participant 2", out)

    def test_reports_a_missing_file(self):
        code, _, err = run_cli(["score", "bfi2", "--input", "/nonexistent/x.csv"])
        self.assertEqual(code, EXIT_MISSING_INPUT)
        self.assertIn("no such file", err)

    def test_writes_scores_when_asked(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "scores.csv"
            code, _, _ = run_cli(
                [
                    "score",
                    "bfi2",
                    "--input",
                    str(FIXTURE_DIR / "test_bfi2_answers.npy"),
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(code, EXIT_OK)
            self.assertTrue(output.exists())

    def test_wrong_instrument_width_is_reported(self):
        code, _, err = run_cli(
            ["score", "vasf", "--input", str(FIXTURE_DIR / "test_bfi2_answers.npy")]
        )
        self.assertEqual(code, 2)
        self.assertIn("18 items", err)


class TestScoreFormats(unittest.TestCase):
    """Every documented response format loads."""

    def test_scores_a_json_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answers.json"
            path.write_text(json.dumps([[3] * 60]), encoding="utf-8")
            code, out, _ = run_cli(["score", "bfi2", "--input", str(path)])
            self.assertEqual(code, EXIT_OK)
            self.assertIn("openness", out)

    def test_rejects_an_unsupported_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answers.parquet"
            path.write_bytes(b"not really parquet")
            code, _, err = run_cli(["score", "bfi2", "--input", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("unsupported response format", err)


class TestStreamSeparation(unittest.TestCase):
    """Diagnostics must not pollute stdout, so output stays pipeable."""

    def test_json_listing_is_parseable_with_diagnostics_enabled(self):
        _, out, _ = run_cli(["--verbose", "list", "--json"])
        json.loads(out)


class TestLegacyTranslation(unittest.TestCase):
    """The pre-2.0 flat command line still works."""

    def test_warns_and_translates(self):
        from personality_questionnaire.cli.main import _translate_legacy

        translated = _translate_legacy(
            ["--questionnaire", "bfi2", "--participant_id", "P01", "--output_dir", "out"]
        )
        self.assertEqual(translated[:2], ["run", "bfi2"])
        self.assertIn("--participant", translated)
        self.assertIn("P01", translated)

    def test_carries_the_vasf_tag(self):
        from personality_questionnaire.cli.main import _translate_legacy

        translated = _translate_legacy(
            ["--questionnaire", "vasf", "--participant_id", "P02", "--vasf_tag", "pre"]
        )
        self.assertIn("--tag", translated)
        self.assertIn("pre", translated)

    def test_ignores_a_questionnaire_filter_on_a_subcommand(self):
        """`records` and `export` take a --questionnaire filter of their own.

        Treating the flag alone as the legacy marker turned `pq records
        --questionnaire panas` into an interactive run, which blocked on stdin.
        """
        from personality_questionnaire.cli.main import _translate_legacy

        for command in ("records", "export"):
            with self.subTest(command=command):
                self.assertIsNone(_translate_legacy([command, "--questionnaire", "panas"]))

    def test_leaves_the_new_form_alone(self):
        from personality_questionnaire.cli.main import _translate_legacy

        self.assertIsNone(_translate_legacy(["list"]))
        self.assertIsNone(_translate_legacy(["run", "bfi2", "--participant", "P1"]))

    def test_skip_questions_does_not_swallow_the_next_flag(self):
        """``--skip_questions`` took no value, so the token after it is its own flag."""
        from personality_questionnaire.cli.main import _translate_legacy

        translated = _translate_legacy(
            ["--questionnaire", "bfi2", "--skip_questions", "--participant_id", "P05"]
        )
        self.assertIn("P05", translated)

    def test_falls_back_when_no_participant_is_given(self):
        from personality_questionnaire.cli.main import _translate_legacy

        self.assertIn("unknown", _translate_legacy(["--questionnaire", "bfi2"]))

    def test_ignores_a_dangling_questionnaire_flag(self):
        from personality_questionnaire.cli.main import _translate_legacy

        self.assertIsNone(_translate_legacy(["--questionnaire"]))


class TestVersion(unittest.TestCase):
    """``--version`` reports the package version."""

    def test_reports_version(self):
        from personality_questionnaire import __version__

        with self.assertRaises(SystemExit), contextlib.redirect_stdout(stdio.StringIO()) as out:
            main(["--version"])
        self.assertIn(__version__, out.getvalue())


if __name__ == "__main__":
    unittest.main()
