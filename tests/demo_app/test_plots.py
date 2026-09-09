"""Tests for chart selection and rendering."""

from __future__ import annotations

import unittest

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

import personality_questionnaire as pq
from demo import plots


class TestIsBigFive(unittest.TestCase):
    """Detecting a Big Five-shaped instrument, generically."""

    def test_bfi2_is_big_five(self):
        self.assertTrue(plots.is_big_five(pq.get("bfi2")))

    def test_bfi10_is_big_five(self):
        self.assertTrue(plots.is_big_five(pq.get("bfi10")))

    def test_bfi2_xs_is_big_five(self):
        self.assertTrue(plots.is_big_five(pq.get("bfi2-xs")))

    def test_panas_is_not_big_five(self):
        self.assertFalse(plots.is_big_five(pq.get("panas")))

    def test_vasf_is_not_big_five(self):
        self.assertFalse(plots.is_big_five(pq.get("vasf")))


class TestPlotFor(unittest.TestCase):
    """Dispatching to the right chart and producing a real figure."""

    def _score(self, key: str, value: int):
        instrument = pq.get(key)
        answers = [value] * instrument.n_items
        return instrument, pq.score(instrument, [answers])

    def test_big_five_instrument_returns_a_figure(self):
        instrument, result = self._score("bfi10", 3)
        figure = plots.plot_for(instrument, result)
        try:
            self.assertIsInstance(figure, Figure)
        finally:
            import matplotlib.pyplot as plt

            plt.close(figure)

    def test_non_big_five_instrument_returns_a_figure(self):
        instrument, result = self._score("panas", 3)
        figure = plots.plot_for(instrument, result)
        try:
            self.assertIsInstance(figure, Figure)
        finally:
            import matplotlib.pyplot as plt

            plt.close(figure)

    def test_radar_chart_has_one_axis_per_domain(self):
        instrument, result = self._score("bfi2-xs", 4)
        figure = plots.plot_for(instrument, result)
        try:
            ax = figure.axes[0]
            self.assertEqual(len(ax.get_xticklabels()), 5)
        finally:
            import matplotlib.pyplot as plt

            plt.close(figure)

    def test_bar_chart_has_one_bar_per_top_level_subscale(self):
        instrument, result = self._score("vasf", 5)
        figure = plots.plot_for(instrument, result)
        try:
            ax = figure.axes[0]
            top_level = instrument.subscales_at(instrument.levels[0])
            self.assertEqual(len(ax.patches), len(top_level))
        finally:
            import matplotlib.pyplot as plt

            plt.close(figure)


if __name__ == "__main__":
    unittest.main()
