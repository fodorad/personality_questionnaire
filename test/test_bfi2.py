import unittest
import numpy as np
from personality_questionnaire import DATA_DIR
from personality_questionnaire.bfi2 import bfi2


class DataloaderTestCase(unittest.TestCase):

    def setUp(self):
        self.data = np.load(DATA_DIR / 'answers.npy')
        self.ocean = np.array([[0.521, 0.646, 0.417, 0.604, 0.250],
                               [0.583, 0.208, 0.729, 0.438, 0.604]])

    def test_bfi2_shapes(self):
        d = bfi2(self.data)
        self.assertEqual(d['OCEAN'].shape, (2, 5))
        self.assertEqual(d['FACET'].shape, (2, 15))

    def test_bfi2_ocean_values(self):
        d = bfi2(self.data)
        np.testing.assert_allclose(np.round(d['OCEAN'], decimals=3), self.ocean)


if __name__ == '__main__':
    unittest.main()