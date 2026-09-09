"""Tests for the theme tokens.

The contrast assertions are the point of this module: a participant reads sixty
items off this palette, so a colour tweak that drops a pairing below WCAG AA should
fail here rather than in someone's eyes.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from personality_questionnaire.core import theme

AA_NORMAL_TEXT = 4.5
"""WCAG 2.1 AA minimum contrast for normal-size text."""

AA_LARGE_TEXT = 3.0
"""WCAG 2.1 AA minimum contrast for large text and UI components."""

LOGO_PATH = Path(__file__).resolve().parents[2] / "docs" / "assets" / "logo.svg"
"""The standalone mark, which must stay identical to the inline one."""

LOGO_PNG_PATH = Path(__file__).resolve().parents[2] / "docs" / "assets" / "logo.png"
"""The raster fallback the README points at.

PyPI strips SVG from project descriptions, so the README cannot use the SVG the way
GitHub and the docs site do. Regenerate with ``make logo`` after editing the SVG.
"""

README_PATH = Path(__file__).resolve().parents[2] / "README.md"
"""The README, whose logo reference must survive PyPI's sanitiser."""


class TestContrast(unittest.TestCase):
    """Every pairing the interface actually uses must meet AA."""

    def test_body_text_on_paper(self):
        self.assertGreaterEqual(theme.contrast_ratio(theme.INK, theme.PAPER), AA_NORMAL_TEXT)

    def test_secondary_text_on_paper(self):
        self.assertGreaterEqual(theme.contrast_ratio(theme.NEUTRAL, theme.PAPER), AA_NORMAL_TEXT)

    def test_header_text_on_primary(self):
        self.assertGreaterEqual(
            theme.contrast_ratio(theme.HEADER_FG, theme.PRIMARY), AA_NORMAL_TEXT
        )

    def test_white_on_every_semantic_fill(self):
        for name in ("primary", "accent", "success", "warning", "danger"):
            with self.subTest(color=name):
                self.assertGreaterEqual(
                    theme.contrast_ratio("#FFFFFF", theme.color(name)), AA_NORMAL_TEXT
                )

    def test_every_semantic_color_on_paper(self):
        for name in ("primary", "accent", "success", "warning", "danger", "neutral"):
            with self.subTest(color=name):
                self.assertGreaterEqual(
                    theme.contrast_ratio(theme.color(name), theme.PAPER), AA_NORMAL_TEXT
                )

    def test_domain_colors_are_readable_on_paper(self):
        for domain, value in theme.DOMAIN_COLORS.items():
            with self.subTest(domain=domain):
                self.assertGreaterEqual(theme.contrast_ratio(value, theme.PAPER), AA_LARGE_TEXT)


class TestContrastRatio(unittest.TestCase):
    """The ratio helper itself."""

    def test_black_on_white_is_the_maximum(self):
        self.assertAlmostEqual(theme.contrast_ratio("#000000", "#FFFFFF"), 21.0, places=1)

    def test_identical_colors_are_one(self):
        self.assertAlmostEqual(theme.contrast_ratio("#12294B", "#12294B"), 1.0, places=6)

    def test_is_symmetric(self):
        self.assertAlmostEqual(
            theme.contrast_ratio(theme.INK, theme.PAPER),
            theme.contrast_ratio(theme.PAPER, theme.INK),
        )

    def test_accepts_values_without_a_hash(self):
        self.assertAlmostEqual(theme.contrast_ratio("000000", "FFFFFF"), 21.0, places=1)


class TestPalette(unittest.TestCase):
    """Token shape and lookup."""

    def test_every_token_is_a_six_digit_hex(self):
        pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for name in ("primary", "accent", "success", "warning", "danger", "neutral"):
            with self.subTest(color=name):
                self.assertRegex(theme.color(name), pattern)

    def test_grounds_are_hex(self):
        for value in (theme.PAPER, theme.INK, theme.HEADER_FG):
            self.assertRegex(value, r"^#[0-9A-Fa-f]{6}$")

    def test_lookup_rejects_an_unknown_name(self):
        with self.assertRaisesRegex(KeyError, "primary"):
            theme.color("chartreuse")

    def test_semantic_colors_are_distinct(self):
        values = [
            theme.color(n) for n in ("primary", "accent", "success", "warning", "danger", "neutral")
        ]
        self.assertEqual(len(values), len(set(values)))

    def test_one_domain_color_per_big_five_domain(self):
        from personality_questionnaire import get

        domains = {s.name for s in get("bfi2").subscales_at("domain")}
        self.assertEqual(set(theme.DOMAIN_COLORS), domains)


class TestLogoMark(unittest.TestCase):
    """The inline mark and the shipped file must not drift apart."""

    def test_is_well_formed_xml(self):
        import xml.dom.minidom

        xml.dom.minidom.parseString(theme.LOGO_MARK_SVG)

    def test_scales_to_its_container(self):
        self.assertIn("width:100%", theme.LOGO_MARK_SVG)

    def test_carries_an_accessible_label(self):
        self.assertIn('role="img"', theme.LOGO_MARK_SVG)
        self.assertIn("aria-label", theme.LOGO_MARK_SVG)

    def test_uses_only_theme_colors(self):
        used = set(re.findall(r"#[0-9A-Fa-f]{6}", theme.LOGO_MARK_SVG))
        self.assertEqual(used, {theme.PRIMARY, theme.ACCENT})

    def test_draws_a_five_by_five_grid(self):
        self.assertEqual(theme.LOGO_MARK_SVG.count('r="3"'), 25)

    def test_shipped_file_uses_the_same_colors(self):
        svg = LOGO_PATH.read_text(encoding="utf-8")
        used = set(re.findall(r"#[0-9A-Fa-f]{6}", svg))
        self.assertEqual(used, {theme.PRIMARY, theme.ACCENT})

    def test_shipped_file_draws_the_same_grid(self):
        svg = LOGO_PATH.read_text(encoding="utf-8")
        self.assertEqual(svg.count('r="3"'), 25)


class TestCoverageGates(unittest.TestCase):
    """The coverage floor is stated in three places and they must agree.

    A mismatch is silent: coverage could pass locally at 90 while Codecov enforces
    something else, or the CI upload could be gated on a Python version the matrix
    does not build, in which case no report is ever published.
    """

    ROOT = Path(__file__).resolve().parents[2]
    FLOOR = 90

    def test_pyproject_sets_the_floor(self):
        text = (self.ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f"fail_under = {self.FLOOR}", text)

    def test_codecov_project_target_matches(self):
        text = (self.ROOT / "codecov.yml").read_text(encoding="utf-8")
        self.assertIn(f"target: {self.FLOOR}%", text)

    def test_codecov_range_starts_at_the_floor(self):
        text = (self.ROOT / "codecov.yml").read_text(encoding="utf-8")
        self.assertIn(f'range: "{self.FLOOR}...100"', text)

    def test_upload_runs_on_a_version_the_matrix_builds(self):
        """Gating the upload on an unbuilt version means it never runs."""
        workflow = (self.ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        gate = re.search(r"matrix\.python-version == '([\d.]+)'", workflow)
        self.assertIsNotNone(gate, "no Codecov upload gate found")
        matrix = re.search(r"python-version: \[([^\]]+)\]", workflow)
        built = {v.strip().strip("\"'") for v in matrix.group(1).split(",")}
        self.assertIn(gate.group(1), built)

    def test_readme_carries_the_coverage_badge(self):
        readme = (self.ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("codecov.io/gh/fodorad/personality_questionnaire", readme)


class TestReadmeLogo(unittest.TestCase):
    """The README's mark has to survive PyPI, which GitHub's does not test."""

    def test_raster_fallback_exists(self):
        self.assertTrue(
            LOGO_PNG_PATH.exists(), "run `make logo` to regenerate docs/assets/logo.png"
        )

    def test_raster_fallback_is_a_png(self):
        self.assertEqual(LOGO_PNG_PATH.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_readme_references_the_png_not_the_svg(self):
        """PyPI silently drops an SVG logo; the README must not depend on one."""
        readme = README_PATH.read_text(encoding="utf-8")
        logo_tag = next(
            line for line in readme.splitlines() if "docs/assets/logo" in line and "<img" in line
        )
        self.assertIn("logo.png", logo_tag)
        self.assertNotIn("logo.svg", logo_tag)

    def test_raster_has_transparent_rounded_corners(self):
        """The plate is rounded, so the extreme corner pixel must be transparent."""
        import struct
        import zlib

        data = LOGO_PNG_PATH.read_bytes()
        pos, idat = 8, b""
        while pos < len(data):
            length = struct.unpack(">I", data[pos : pos + 4])[0]
            tag = data[pos + 4 : pos + 8]
            if tag == b"IHDR":
                width, _, _, colour_type = struct.unpack(">IIBB", data[pos + 8 : pos + 18])
            elif tag == b"IDAT":
                idat += data[pos + 8 : pos + 8 + length]
            pos += 12 + length

        self.assertEqual(colour_type, 6, "logo.png must carry an alpha channel")
        first_row = zlib.decompress(idat)[1 : 1 + width * 4]
        self.assertEqual(first_row[3], 0, "top-left corner should be transparent")

    def test_readme_logo_url_is_absolute(self):
        """A relative path resolves against pypi.org and 404s."""
        readme = README_PATH.read_text(encoding="utf-8")
        logo_tag = next(
            line for line in readme.splitlines() if "docs/assets/logo" in line and "<img" in line
        )
        self.assertIn("https://raw.githubusercontent.com/", logo_tag)


if __name__ == "__main__":
    unittest.main()
