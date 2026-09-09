"""Tests for record provenance."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from personality_questionnaire import __version__, get
from personality_questionnaire import provenance as provenance_module
from personality_questionnaire.provenance import capture, instrument_hash


class TestCapture(unittest.TestCase):
    """The runtime snapshot records what produced a record."""

    def test_reports_the_package_version(self):
        self.assertEqual(capture().package_version, __version__)

    def test_timestamp_is_timezone_aware_utc(self):
        captured = capture(refresh=True).captured_at
        self.assertIsNotNone(captured.tzinfo)
        self.assertEqual(captured.utcoffset(), datetime.now(UTC).utcoffset())

    def test_is_cached(self):
        self.assertIs(capture(), capture())

    def test_git_sha_is_absent_or_a_full_hash(self):
        sha = capture().git_sha
        if sha is not None:
            self.assertEqual(len(sha), 40)
            self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_survives_git_being_unavailable(self):
        original = provenance_module._git
        provenance_module._git = lambda *args: None
        try:
            snapshot = capture(refresh=True)
            self.assertIsNone(snapshot.git_sha)
            self.assertFalse(snapshot.git_dirty)
        finally:
            provenance_module._git = original
            capture(refresh=True)

    def test_serialises_to_json_friendly_types(self):
        payload = capture().as_dict()
        self.assertIsInstance(payload["captured_at"], str)
        self.assertIn("package_version", payload)


class TestInstrumentHash(unittest.TestCase):
    """The hash pins exactly what was administered."""

    def test_is_stable(self):
        self.assertEqual(instrument_hash(get("bfi2")), instrument_hash(get("bfi2")))

    def test_differs_between_instruments(self):
        self.assertNotEqual(instrument_hash(get("bfi2")), instrument_hash(get("vasf")))

    def test_is_prefixed(self):
        self.assertTrue(instrument_hash(get("bfi2")).startswith("sha256:"))

    def test_changes_when_an_item_changes(self):
        import dataclasses

        original = get("bfi2")
        edited = dataclasses.replace(
            original,
            items=(dataclasses.replace(original.items[0], text="changed"), *original.items[1:]),
        )
        self.assertNotEqual(instrument_hash(original), instrument_hash(edited))


if __name__ == "__main__":
    unittest.main()
