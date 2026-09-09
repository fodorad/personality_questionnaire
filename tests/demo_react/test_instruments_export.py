"""The checked-in demo-react/src/instruments.json must not drift.

scripts/export_instruments.py is run by hand and its output committed, like
docs/assets/logo.png -- so an instrument change in Python that forgets to
regenerate the JSON would otherwise ship a stale React demo silently. This
fails CI instead.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import scripts.export_instruments as export_instruments
from scripts.export_instruments import OUTPUT_PATH, export_all

ROOT = Path(__file__).resolve().parents[2]


class TestInstrumentsExportIsFresh(unittest.TestCase):
    """The committed JSON matches what the export script produces right now."""

    def test_checked_in_json_matches_a_fresh_export(self):
        checked_in_path = ROOT / OUTPUT_PATH
        self.assertTrue(
            checked_in_path.exists(),
            "run `make export-instruments` to generate demo-react/src/instruments.json",
        )
        checked_in = json.loads(checked_in_path.read_text(encoding="utf-8"))
        fresh = export_all()
        self.assertEqual(
            checked_in,
            fresh,
            "demo-react/src/instruments.json is stale -- run `make export-instruments`",
        )


class TestMainWritesTheFile(unittest.TestCase):
    """main() actually creates the parent directory and writes valid JSON.

    Points the module's OUTPUT_PATH at a throwaway directory for the
    duration of the test rather than mocking file I/O, so this exercises the
    real mkdir/write_text path -- the two lines the drift check above never
    touches, since it calls export_all() directly.
    """

    def setUp(self):
        self.original_output_path = export_instruments.OUTPUT_PATH
        self.tmp_dir = Path(tempfile.mkdtemp())
        export_instruments.OUTPUT_PATH = self.tmp_dir / "nested" / "instruments.json"

    def tearDown(self):
        export_instruments.OUTPUT_PATH = self.original_output_path
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_main_creates_parent_directory_and_writes_matching_json(self):
        export_instruments.main()

        written_path = export_instruments.OUTPUT_PATH
        self.assertTrue(written_path.exists())
        self.assertEqual(json.loads(written_path.read_text(encoding="utf-8")), export_all())


if __name__ == "__main__":
    unittest.main()
