"""Tests for reading and writing responses and scores."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import personality_questionnaire as pq
from personality_questionnaire.bfi2 import BFI2_QUESTIONNAIRE
from personality_questionnaire.io import (
    load_csv,
    load_csv_int,
    load_csv_str,
    load_json,
    load_tsv,
    save_csv,
    save_csv_int,
    save_json,
)
from tests.fixtures import FIXTURE_DIR


class TestLoaders(unittest.TestCase):
    """The pre-2.0 file formats still load."""

    def test_int_and_label_files_agree(self):
        from_int = load_csv_int(FIXTURE_DIR / "test_bfi2_answers_int.csv", 60)
        from_str = load_csv_str(FIXTURE_DIR / "test_bfi2_answers_str.csv", 60)
        from_npy = np.load(FIXTURE_DIR / "test_bfi2_answers.npy")
        self.assertEqual(from_int.shape, (2, 60))
        np.testing.assert_array_equal(from_int, from_str)
        np.testing.assert_array_equal(from_int, from_npy)

    def test_shipped_tsv_matches_the_canonical_items(self):
        shipped = load_tsv(pq.asset("bfi-2_questionnaire.tsv"))
        self.assertEqual(shipped, BFI2_QUESTIONNAIRE)

    def test_reports_a_short_row_with_its_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short.csv"
            path.write_text("1,2,3\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2 has 2 values"):
                load_csv_int(path, 3)

    def test_reports_an_unconvertible_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("1,2,x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1 is not convertible"):
                load_csv_int(path, 3)

    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blanks.csv"
            path.write_text("1,2,3\n\n4,5,6\n", encoding="utf-8")
            self.assertEqual(load_csv_int(path, 3).shape, (2, 3))

    def test_empty_file_yields_an_empty_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.csv"
            path.write_text("", encoding="utf-8")
            self.assertEqual(load_csv_int(path, 3).shape, (0, 3))


class TestWriters(unittest.TestCase):
    """Writers round-trip and create their parent directories."""

    def test_int_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "answers.csv"
            save_csv_int(path, [[1, 2, 3], [4, 5, 6]])
            np.testing.assert_array_equal(load_csv_int(path, 3), [[1, 2, 3], [4, 5, 6]])

    def test_scores_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.csv"
            save_csv(path, np.array([[0.25, 0.5]]))
            restored = load_csv(path, 2, float)
            np.testing.assert_allclose(restored, [[0.25, 0.5]])

    def test_writes_one_line_per_row(self):
        """``newline=""`` keeps the csv module from doubling line endings.

        Without it the writer emits ``\r\n`` and the file layer translates the
        ``\n`` again, leaving a blank line between every row on Windows.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "answers.csv"
            save_csv_int(path, [[1, 2], [3, 4]])
            raw = path.read_bytes()
            self.assertNotIn(b"\n\n", raw)
            self.assertEqual(len(raw.splitlines()), 2)

    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            payload = {"participant": "P01", "responses": [1, 2, 3]}
            self.assertEqual(save_json(path, payload), path)
            self.assertEqual(load_json(path), payload)


class TestAssets(unittest.TestCase):
    """Shipped data resolves through importlib.resources."""

    def test_asset_is_readable(self):
        self.assertIn("Is outgoing", pq.asset("bfi-2_questionnaire.tsv").read_text())

    def test_data_dir_is_deprecated(self):
        with self.assertWarns(DeprecationWarning):
            _ = pq.DATA_DIR

    def test_unknown_attribute_still_raises(self):
        with self.assertRaises(AttributeError):
            _ = pq.does_not_exist


if __name__ == "__main__":
    unittest.main()
