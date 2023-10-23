import os
import csv
import numpy as np
from personality_questionnaire.bfi2 import ANSWER


PathType = str | os.PathLike


def load_csv(csv_path: PathType, conversion_fn) -> np.ndarray:

    scores = np.zeros(shape=(0,60))
    with open(csv_path, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            new_participant = np.expand_dims(np.array(list(map(conversion_fn, row))), axis=0)
            scores = np.concatenate((scores, new_participant), axis=0)

    return scores


def load_csv_int(csv_path: PathType) -> np.ndarray:
    return load_csv(csv_path, int)


def load_csv_str(csv_path: PathType) -> np.ndarray:
    return load_csv(csv_path, lambda x: ANSWER[x])


def load_tsv(tsv_path: PathType) -> dict[int, str]:

    with open(tsv_path, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)
        questionnaire = {int(row[0]): row[1] for row in reader}

    return questionnaire