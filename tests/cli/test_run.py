"""Tests for the interactive ``pq run`` command and its side-car files."""

from __future__ import annotations

import contextlib
import io as stdio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from personality_questionnaire import io
from personality_questionnaire.cli.main import (
    EXIT_ABORTED,
    EXIT_NOT_INTERACTIVE,
    EXIT_OK,
    build_parser,
    main,
)


def administer(argv: list[str], responses: list[str], *, db: str | None = None) -> tuple[int, str]:
    """Run ``pq run`` with a scripted participant.

    Drives the injected ``read``/``write`` seam rather than patching anything, so
    the test exercises the same call path a real participant would.

    Args:
        argv: Arguments after the program name.
        responses: Lines the participant types, in order.

    Returns:
        The exit code and everything written to the participant.
    """
    lines = iter(responses)
    transcript: list[str] = []

    # `run` persists by default. Every test gets a throwaway database so a run can
    # never touch the operator's real records.
    argv = [*argv, "--db", db or "sqlite://"] if "--db" not in argv else argv

    args = build_parser().parse_args(argv)
    args.read = lambda _: next(lines)
    args.write = transcript.append

    out = stdio.StringIO()
    with contextlib.redirect_stdout(out):
        code = int(args.func(args))

    return code, "\n".join(transcript) + out.getvalue()


class TestRun(unittest.TestCase):
    """Administering an instrument end to end."""

    def test_scores_and_reports(self):
        code, output = administer(["run", "bfi2", "--participant", "P01"], ["3"] * 60)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("openness", output)

    def test_abandoning_saves_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = administer(
                ["run", "bfi2", "--participant", "P01", "--output-dir", directory],
                ["quit"],
            )
            self.assertEqual(code, EXIT_ABORTED)
            self.assertIn("nothing was saved", output)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_writes_side_cars_when_asked(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _ = administer(
                ["run", "bfi2", "--participant", "P07", "--output-dir", directory],
                ["4"] * 60,
            )
            self.assertEqual(code, EXIT_OK)

            answers = Path(directory) / "P07_bfi2_answers_int.csv"
            self.assertTrue(answers.exists())
            self.assertTrue((Path(directory) / "P07_bfi2_scores.csv").exists())
            self.assertEqual(io.load_csv_int(answers, 60).shape, (1, 60))

    def test_recorded_answers_match_what_was_typed(self):
        with tempfile.TemporaryDirectory() as directory:
            administer(
                ["run", "vasf", "--participant", "P03", "--output-dir", directory],
                [str(i % 11) for i in range(18)],
            )
            saved = io.load_csv_int(Path(directory) / "P03_vasf_answers_int.csv", 18)
            self.assertEqual(list(saved[0]), [i % 11 for i in range(18)])

    def test_tag_appears_in_the_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            administer(
                [
                    "run",
                    "vasf",
                    "--participant",
                    "P02",
                    "--tag",
                    "pre",
                    "--output-dir",
                    directory,
                ],
                ["5"] * 18,
            )
            self.assertTrue((Path(directory) / "P02_vasf-pre_answers_int.csv").exists())

    def test_writes_nothing_without_an_output_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path.cwd()
            os.chdir(directory)
            try:
                administer(["run", "bfi2", "--participant", "P01"], ["3"] * 60)
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                os.chdir(cwd)


class TestExhaustedInput(unittest.TestCase):
    """``run`` fails fast when input runs out instead of blocking on it.

    Without the guard the command waits forever on ``input()`` with no output --
    the failure mode that hung a test run for two minutes during review. Piping
    answers in stays supported; only *running out* of them is an error, because a
    partial questionnaire cannot be scored.
    """

    @staticmethod
    def _run_detached(argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
        """Invoke the CLI in a child process, optionally piping stdin.

        Args:
            argv: Arguments after the program name.
            stdin: Text to pipe in. ``None`` closes stdin entirely.

        Returns:
            The completed process.

        Raises:
            AssertionError: If the child does not exit promptly, which is exactly
                the hang this guard prevents.
        """
        try:
            return subprocess.run(
                [sys.executable, "-m", "personality_questionnaire.cli.main", *argv],
                input=stdin,
                stdin=None if stdin is not None else subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).resolve().parents[2],
            )
        except subprocess.TimeoutExpired:  # pragma: no cover - the bug being guarded
            raise AssertionError("`pq run` blocked on a non-interactive stdin") from None

    def test_closed_stdin_exits_rather_than_blocking(self):
        completed = self._run_detached(["run", "bfi2", "--participant", "P01"])
        self.assertEqual(completed.returncode, EXIT_NOT_INTERACTIVE)

    def test_points_at_the_command_that_does_work(self):
        completed = self._run_detached(["run", "bfi2", "--participant", "P01"])
        self.assertIn("pq score bfi2", completed.stderr)

    def test_names_the_item_input_ran_out_at(self):
        completed = self._run_detached(["run", "bfi2", "--participant", "P01"], stdin="3\n" * 10)
        self.assertEqual(completed.returncode, EXIT_NOT_INTERACTIVE)
        self.assertIn("item 11 of 60", completed.stderr)

    def test_piped_answers_are_still_scored(self):
        """Scripting an administration through a pipe must keep working."""
        completed = self._run_detached(["run", "vasf", "--participant", "P01"], stdin="5\n" * 18)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Fatigue", completed.stdout)

    def test_other_commands_still_work_non_interactively(self):
        completed = self._run_detached(["list"])
        self.assertEqual(completed.returncode, 0)
        self.assertIn("bfi2", completed.stdout)


class TestApiShim(unittest.TestCase):
    """The pre-2.0 module path still resolves."""

    def test_api_exports_main(self):
        from personality_questionnaire import api

        self.assertIs(api.main, main)

    def test_run_wrapper_exits(self):
        from personality_questionnaire.cli.main import run

        with self.assertRaises(SystemExit), contextlib.redirect_stdout(stdio.StringIO()):
            run()


if __name__ == "__main__":
    unittest.main()
