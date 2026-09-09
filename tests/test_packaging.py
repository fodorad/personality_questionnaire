"""Tests that the built distribution actually contains what it needs.

A guard that never runs is not a guard: these build a real wheel and import it in
a clean interpreter, because the 1.x packaging bug -- data resolved relative to the
repository root, so an installed wheel pointed at a directory that had never
shipped -- was invisible to every test that ran from a source checkout.

Building is slow, so the suite is opt-in: set ``RUN_PACKAGING_TESTS=1``. CI sets it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
"""The repository root, where the build is run from."""

RUN_PACKAGING_TESTS = os.environ.get("RUN_PACKAGING_TESTS") == "1"
"""Whether to run the slow build-and-install checks."""


def _build_wheel(out_dir: str) -> None:
    """Build a wheel into ``out_dir``.

    Prefers ``uv build`` -- the project's own build path, and the one CI uses --
    falling back to ``python -m build`` where uv is unavailable.

    Args:
        out_dir: Directory to write the wheel into.

    Raises:
        unittest.SkipTest: If neither builder is available.
    """
    for command in (
        ["uv", "build", "--wheel", "--out-dir", out_dir],
        [sys.executable, "-m", "build", "--wheel", "--outdir", out_dir],
    ):
        try:
            subprocess.run(command, cwd=REPO_ROOT, check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            continue
        return

    raise unittest.SkipTest("no wheel builder available (need uv or python -m build)")


@unittest.skipUnless(RUN_PACKAGING_TESTS, "set RUN_PACKAGING_TESTS=1 to run")
class TestWheelContents(unittest.TestCase):
    """The wheel must carry the package's data and type marker."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        _build_wheel(cls._tmp.name)
        cls.wheel = next(Path(cls._tmp.name).glob("*.whl"))
        with zipfile.ZipFile(cls.wheel) as archive:
            cls.names = set(archive.namelist())

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_ships_the_item_table(self):
        self.assertIn("personality_questionnaire/assets/bfi-2_questionnaire.tsv", self.names)

    def test_ships_the_type_marker(self):
        self.assertIn("personality_questionnaire/py.typed", self.names)

    def test_ships_every_instrument_module(self):
        for module in ("bfi2", "vasf"):
            with self.subTest(module=module):
                self.assertIn(f"personality_questionnaire/instruments/{module}.py", self.names)

    def test_does_not_ship_the_tests(self):
        self.assertFalse([name for name in self.names if name.startswith("tests/")])


@unittest.skipUnless(RUN_PACKAGING_TESTS, "set RUN_PACKAGING_TESTS=1 to run")
class TestInstalledImport(unittest.TestCase):
    """The installed package must resolve its data outside a source checkout."""

    def test_asset_resolves_from_an_installed_wheel(self):
        with tempfile.TemporaryDirectory() as directory:
            _build_wheel(directory)
            wheel = next(Path(directory).glob("*.whl"))
            venv = Path(directory) / "venv"
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            python = venv / ("Scripts" if os.name == "nt" else "bin") / "python"
            subprocess.run([str(python), "-m", "pip", "install", "--quiet", str(wheel)], check=True)

            # Run from a directory that is not the checkout, so a path-relative
            # lookup would fail exactly as it did before 2.0.
            completed = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import personality_questionnaire as pq;"
                    "print(len(pq.asset('bfi-2_questionnaire.tsv').read_text()));"
                    "print(pq.score(pq.get('bfi2'), [[3]*60]).as_dict()['openness'])",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                check=True,
            )
            length, score = completed.stdout.split()
            self.assertGreater(int(length), 0)
            self.assertAlmostEqual(float(score), 0.5)


if __name__ == "__main__":
    unittest.main()
