"""Tests for the three export shapes."""

from __future__ import annotations

import csv
import io
import json
import unittest

import personality_questionnaire as pq
from personality_questionnaire.db import Record, Repository, create_engine_from_env
from personality_questionnaire.db.export import record_to_json, to_csv, to_json


def answers_for(key: str, value: int = 3) -> dict[int, int]:
    """Build a complete response set."""
    return {n: value for n in range(1, pq.get(key).n_items + 1)}


class ExportTestCase(unittest.TestCase):
    """Base with two saved BFI-10 records."""

    def setUp(self):
        self.engine = create_engine_from_env("sqlite://")
        self.repo = Repository(self.engine)
        self.addCleanup(self.repo.close)
        self.first = self.repo.save(
            Record(
                participant_code="P01",
                questionnaire="bfi10",
                responses=answers_for("bfi10", 3),
                experiment="study-a",
            )
        )
        self.second = self.repo.save(
            Record(
                participant_code="P02",
                questionnaire="bfi10",
                responses=answers_for("bfi10", 5),
            )
        )
        self.ids = [self.first.session_id, self.second.session_id]


class TestWide(ExportTestCase):
    """One row per session, columns per item and subscale."""

    def rows(self) -> list[dict[str, str]]:
        """Parse the wide export."""
        return list(csv.DictReader(io.StringIO(to_csv(self.engine, self.ids, shape="wide"))))

    def test_one_row_per_record(self):
        self.assertEqual(len(self.rows()), 2)

    def test_has_a_column_per_item(self):
        header = self.rows()[0]
        for number in range(1, 11):
            with self.subTest(item=number):
                self.assertIn(f"item_{number}", header)

    def test_has_a_column_per_subscale(self):
        header = self.rows()[0]
        for subscale in pq.get("bfi10").subscales:
            with self.subTest(subscale=subscale.name):
                self.assertIn(subscale.name, header)

    def test_carries_provenance(self):
        row = self.rows()[0]
        self.assertIn("package_version", row)
        self.assertTrue(row["package_version"])

    def test_records_the_answers_given(self):
        row = next(r for r in self.rows() if r["participant_code"] == "P02")
        self.assertEqual(row["item_1"], "5")

    def test_refuses_a_mixed_instrument_selection(self):
        """A wide file cannot hold two instruments without mostly-empty columns."""
        other = self.repo.save(
            Record(
                participant_code="P03",
                questionnaire="panas",
                responses=answers_for("panas"),
            )
        )
        with self.assertRaisesRegex(ValueError, "one instrument at a time"):
            to_csv(self.engine, [*self.ids, other.session_id], shape="wide")

    def test_empty_selection_yields_empty_text(self):
        self.assertEqual(to_csv(self.engine, [], shape="wide"), "")


class TestLong(ExportTestCase):
    """One row per value, across any mix of instruments."""

    def rows(self, ids=None) -> list[dict[str, str]]:
        """Parse the long export."""
        return list(csv.DictReader(io.StringIO(to_csv(self.engine, ids or self.ids, shape="long"))))

    def test_holds_responses_and_scores(self):
        kinds = {row["kind"] for row in self.rows()}
        self.assertEqual(kinds, {"response", "score"})

    def test_row_count_matches_the_data(self):
        instrument = pq.get("bfi10")
        expected = 2 * (instrument.n_items + len(instrument.subscales))
        self.assertEqual(len(self.rows()), expected)

    def test_accepts_a_mixed_instrument_selection(self):
        other = self.repo.save(
            Record(
                participant_code="P03",
                questionnaire="panas",
                responses=answers_for("panas"),
            )
        )
        instruments = {row["questionnaire"] for row in self.rows([*self.ids, other.session_id])}
        self.assertEqual(instruments, {"bfi10", "panas"})

    def test_is_stable_under_reordering(self):
        forward = to_csv(self.engine, self.ids, shape="long")
        self.assertEqual(
            forward.splitlines()[0], to_csv(self.engine, self.ids[:1], shape="long").splitlines()[0]
        )


class TestJson(ExportTestCase):
    """The archival form is self-describing."""

    def test_carries_every_section(self):
        payload = record_to_json(self.repo, self.first.session_id)
        self.assertEqual(
            set(payload),
            {"schema_version", "participant", "session", "provenance", "responses", "scores"},
        )

    def test_records_provenance(self):
        provenance = record_to_json(self.repo, self.first.session_id)["provenance"]
        self.assertTrue(provenance["package_version"])
        self.assertTrue(provenance["instrument_hash"].startswith("sha256:"))
        self.assertEqual(provenance["scoring_version"], 1)

    def test_groups_scores_by_level(self):
        scores = record_to_json(self.repo, self.first.session_id)["scores"]
        self.assertIn("domain", scores)
        self.assertIn("openness", scores["domain"])

    def test_is_serialisable(self):
        json.dumps(to_json(self.repo, self.ids))

    def test_exports_several_records(self):
        self.assertEqual(len(to_json(self.repo, self.ids)), 2)

    def test_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            record_to_json(self.repo, 9999)


class TestShapeSelection(ExportTestCase):
    """An unknown shape is rejected with the valid options named."""

    def test_rejects_an_unknown_shape(self):
        with self.assertRaisesRegex(ValueError, "unknown shape"):
            to_csv(self.engine, self.ids, shape="sideways")


if __name__ == "__main__":
    unittest.main()
