import os
import csv
from typing import Sequence, Callable
from pathlib import Path
import numpy as np
from personality_questionnaire.bfi2 import ANSWER


PathType = str | os.PathLike


def load_csv(csv_path: PathType, n_values: int, conversion_fn: Callable) -> np.ndarray:

    scores = np.zeros(shape=(0, n_values))
    with open(csv_path, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            new_participant = np.expand_dims(np.array(list(map(conversion_fn, row))), axis=0)
            scores = np.concatenate((scores, new_participant), axis=0)

    return scores


def load_csv_int(csv_path: PathType, n_values: int) -> np.ndarray:
    return load_csv(csv_path, n_values, int).astype(int)


def load_csv_str(csv_path: PathType, n_values: int) -> np.ndarray:
    return load_csv(csv_path, n_values, lambda x: ANSWER[x])


def load_tsv(tsv_path: PathType) -> dict[int, str]:

    with open(tsv_path, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)
        questionnaire = {int(row[0]): row[1] for row in reader}

    return questionnaire


def save_csv_int(csv_path: PathType, data: Sequence[Sequence]) -> None:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for row in data:
            writer.writerow(row)


def save_csv(csv_path: PathType, data: np.ndarray) -> None:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for row in data:
            writer.writerow(row)