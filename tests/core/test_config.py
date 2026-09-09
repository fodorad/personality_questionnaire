"""Tests for runtime settings.

The host default is the one setting with a safety consequence: participant
self-reports are consent-restricted, so binding off loopback must be deliberate and
must announce itself.
"""

from __future__ import annotations

import os
import unittest

from personality_questionnaire.core.config import LOOPBACK, Settings


class EnvironmentTestCase(unittest.TestCase):
    """Base that restores the environment afterwards."""

    VARIABLES = ("PQ_HOST", "PQ_PORT", "PQ_DATABASE_URL")

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in self.VARIABLES}
        for key in self.VARIABLES:
            os.environ.pop(key, None)
        self.addCleanup(self._restore)

    def _restore(self):
        """Put the environment back."""
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestDefaults(EnvironmentTestCase):
    """Unconfigured settings are the safe ones."""

    def test_binds_loopback_by_default(self):
        self.assertEqual(Settings().host, LOOPBACK)

    def test_default_is_recognised_as_loopback(self):
        self.assertTrue(Settings().is_loopback)

    def test_default_port(self):
        self.assertEqual(Settings().port, 8080)

    def test_does_not_open_a_browser_by_default(self):
        self.assertFalse(Settings().show)

    def test_database_url_is_unset_by_default(self):
        self.assertIsNone(Settings().database_url)


class TestEnvironment(EnvironmentTestCase):
    """Every setting is configurable without editing code."""

    def test_host_from_environment(self):
        os.environ["PQ_HOST"] = "0.0.0.0"  # noqa: S104 - the value under test
        self.assertEqual(Settings().host, "0.0.0.0")  # noqa: S104

    def test_port_from_environment(self):
        os.environ["PQ_PORT"] = "9001"
        self.assertEqual(Settings().port, 9001)

    def test_unparseable_port_falls_back(self):
        """A typo in the environment must not stop the application starting."""
        os.environ["PQ_PORT"] = "not-a-port"
        self.assertEqual(Settings().port, 8080)

    def test_database_url_from_environment(self):
        os.environ["PQ_DATABASE_URL"] = "sqlite:///x.db"
        self.assertEqual(Settings().database_url, "sqlite:///x.db")


class TestExposureWarning(EnvironmentTestCase):
    """Binding off loopback has to announce itself."""

    def test_loopback_addresses_are_silent(self):
        for host in (LOOPBACK, "localhost", "::1"):
            with self.subTest(host=host):
                self.assertIsNone(Settings(host=host).exposure_warning)

    def test_a_routable_address_warns(self):
        warning = Settings(host="0.0.0.0").exposure_warning  # noqa: S104
        self.assertIsNotNone(warning)
        self.assertIn("consent-restricted", warning)

    def test_the_warning_names_the_address(self):
        self.assertIn("192.168.1.10", Settings(host="192.168.1.10").exposure_warning)

    def test_a_routable_address_is_not_loopback(self):
        self.assertFalse(Settings(host="192.168.1.10").is_loopback)


if __name__ == "__main__":
    unittest.main()
