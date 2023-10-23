import unittest
import numpy as np
from personality_questionnaire import DATA_DIR
from personality_questionnaire.dataloader import load_csv_int, load_csv_str, load_tsv
from personality_questionnaire.bfi2 import BFI2_QUESTIONNAIRE


class DataloaderTestCase(unittest.TestCase):

    def test_load_data(self):
        data_from_int = load_csv_int(DATA_DIR / 'answers_int.csv')
        data_from_str = load_csv_str(DATA_DIR / 'answers_str.csv')
        data_from_npy = np.load(DATA_DIR / 'answers.npy')
        self.assertEqual(data_from_int.shape, (2, 60))
        self.assertEqual(data_from_str.shape, (2, 60))
        self.assertEqual(data_from_npy.shape, (2, 60))
        np.testing.assert_allclose(data_from_int, data_from_str)
        np.testing.assert_allclose(data_from_int, data_from_npy)

    def test_load_bfi2_questionnaire(self):
        questionnaire = load_tsv(DATA_DIR / 'bfi-2_questionnaire.tsv')
        self.assertDictEqual(BFI2_QUESTIONNAIRE, questionnaire)


if __name__ == '__main__':
    unittest.main()