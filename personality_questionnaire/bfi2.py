from typing import Sequence
import numpy as np


# Item numbers for the BFI-2 domain and facet scales are listed below. Reverse-keyed items are denoted by “R.”
#
# Citation for the BFI-2
# Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2): Developing and assessing a hierarchical
# model with 15 facets to enhance bandwidth, fidelity, and predictive power. Journal of Personality and Social
# Psychology, 113, 117-143.
BFI2_QUESTIONNAIRE: dict[int, str] = {
    1: 'Is outgoing, sociable.',
    2: 'Is compassionate, has a soft heart.',
    3: 'Tends to be disorganized.',
    4: 'Is relaxed, handles stress well.',
    5: 'Has few artistic interests.',
    6: 'Has an assertive personality.',
    7: 'Is respectful, treats others with respect.',
    8: 'Tends to be lazy.',
    9: 'Stays optimistic after experiencing a setback.',
    10: 'Is curious about many different things.',
    11: 'Rarely feels excited or eager.',
    12: 'Tends to find fault with others.',
    13: 'Is dependable, steady.',
    14: 'Is moody, has up and down mood swings.',
    15: 'Is inventive, finds clever ways to do things.',
    16: 'Tends to be quiet.',
    17: 'Feels little sympathy for others.',
    18: 'Is systematic, likes to keep things in order.',
    19: 'Can be tense.',
    20: 'Is fascinated by art, music, or literature.',
    21: 'Is dominant, acts as a leader.',
    22: 'Starts arguments with others.',
    23: 'Has difficulty getting started on tasks.',
    24: 'Feels secure, comfortable with self.',
    25: 'Avoids intellectual, philosophical discussions.',
    26: 'Is less active than other people.',
    27: 'Has a forgiving nature.',
    28: 'Can be somewhat careless.',
    29: 'Is emotionally stable, not easily upset.',
    30: 'Has little creativity.',
    31: 'Is sometimes shy, introverted.',
    32: 'Is helpful and unselfish with others.',
    33: 'Keeps things neat and tidy.',
    34: 'Worries a lot.',
    35: 'Values art and beauty.',
    36: 'Finds it hard to influence people.',
    37: 'Is sometimes rude to others.',
    38: 'Is efficient, gets things done.',
    39: 'Often feels sad.',
    40: 'Is complex, a deep thinker.',
    41: 'Is full of energy.',
    42: 'Is suspicious of others\' intentions.',
    43: 'Is reliable, can always be counted on.',
    44: 'Keeps their emotions under control.',
    45: 'Has difficulty imagining things.',
    46: 'Is talkative.',
    47: 'Can be cold and uncaring.',
    48: 'Leaves a mess, doesn\'t clean up.',
    49: 'Rarely feels anxious or afraid.',
    50: 'Thinks poetry and plays are boring.',
    51: 'Prefers to have others take charge.',
    52: 'Is polite, courteous to others.',
    53: 'Is persistent, works until the task is finished.',
    54: 'Tends to feel depressed, blue.',
    55: 'Has little interest in abstract ideas.',
    56: 'Shows a lot of enthusiasm.',
    57: 'Assumes the best about people.',
    58: 'Sometimes behaves irresponsibly.',
    59: 'Is temperamental, gets emotional easily.',
    60: 'Is original, comes up with new ideas.',
}


DOMAIN_SCALES: dict[str, list[str]] = {
    'openness':          ['5R', '10', '15', '20', '25R', '30R', '35', '40', '45R', '50R', '55R', '60'],
    'conscientiousness': ['3R', '8R', '13', '18', '23R', '28R', '33', '38', '43', '48R', '53', '58R'],
    'extraversion':      ['1', '6', '11R', '16R', '21', '26R', '31R', '36R', '41', '46', '51R', '56'],
    'agreeableness':     ['2', '7', '12R', '17R', '22R', '27', '32', '37R', '42R', '47R', '52', '57'],
    'neurocitism':       ['4R', '9R', '14', '19', '24R', '29R', '34', '39', '44R', '49R', '54', '59'],
}


FACET_SCALES: dict[str, list[str]] = {
    'Sociability':            ['1', '16R', '31R', '46'],
    'Assertiveness':          ['6', '21', '36R', '51R'],
    'Energy Level':           ['11R', '26R', '41', '56'],
    'Compassion':             ['2', '17R', '32', '47R'],
    'Respectfulness':         ['7', '22R', '37R', '52'],
    'Trust':                  ['12R', '27', '42R', '57'],
    'Organization':           ['3R', '18', '33', '48R'],
    'Productiveness':         ['8R', '23R', '38', '53'],
    'Responsibility':         ['13', '28R', '43', '58R'],
    'Anxiety':                ['4R', '19', '34', '49R'],
    'Depression':             ['9R', '24R', '39', '54'],
    'Emotional Volatility':   ['14', '29R', '44R', '59'],
    'Intellectual Curiosity': ['10', '25R', '40', '55R'],
    'Aesthetic Sensitivity':  ['5R', '20', '35', '50R'],
    'Creative Imagination':   ['15', '30R', '45R', '60'],
}


DOMAIN_SCALES_AS_FACET_SCALES: dict[str, list[str]] = {
    'extraversion':      FACET_SCALES['Sociability']            + FACET_SCALES['Assertiveness']         + FACET_SCALES['Energy Level'],
    'agreeableness':     FACET_SCALES['Compassion']             + FACET_SCALES['Respectfulness']        + FACET_SCALES['Trust'],
    'conscientiousness': FACET_SCALES['Organization']           + FACET_SCALES['Productiveness']        + FACET_SCALES['Responsibility'],
    'neurocitism':       FACET_SCALES['Anxiety']                + FACET_SCALES['Depression']            + FACET_SCALES['Emotional Volatility'],
    'openness':          FACET_SCALES['Intellectual Curiosity'] + FACET_SCALES['Aesthetic Sensitivity'] + FACET_SCALES['Creative Imagination'],
}


ANSWER: dict[str, int] = {
    'Disagree strongly': 1,
    'Disagree a little': 2,
    'Neutral; no opinion': 3,
    'Agree a little': 4,
    'Agree strongly': 5,
}


def _R(value: int) -> int:
    """Reverses a Big Five score.

    Args:
        value (int): score between 1 and 5.

    Returns:
        int: reversed score.
    """
    if not value in set(range(1, 6, 1)):
        raise ValueError('Invalid rating, value must be in the range of [1..5].')

    if value == 1:
        return 5
    elif value == 2:
        return 4
    elif value == 4:
        return 2
    elif value == 5:
        return 1
    else: # 3
        return value


def _process_answer(answer: Sequence, questions: list[str]) -> np.ndarray:
    """Processes a single answer for a given trait's questions.

    Args:
        answer (Sequence): participant's answers given to the items of the questionnaire.
        questions (list[str]): list of item ids.

    Raises:
        ValueError: given answer is not for BFI-2, as it must be a length of 60.

    Returns:
        np.ndarray: scores for the questions.
    """
    if not len(answer) == 60:
        raise ValueError(f'Single answer is expected to be a Sized of length 60 got instead {len(answer)}.')

    values = np.zeros(shape=(len(questions),), dtype=int)
    for index, question in enumerate(questions):
        reversed = 'R' in question
        question_id = question[:-1] if reversed else question
        question_index = int(question_id)-1 # question ids are between [1..60]
        value = int(answer[question_index])

        if reversed:
            value = _R(value)

        values[index] = value

    return values


def bfi2_trait(answers: Sequence[Sequence], questions: list[str]) -> np.ndarray:
    """Calculates the BFI-2 trait values for all answers.
    The mean is calculated from the question scores, then scaled between 0 and 1.

    Args:
        answers (Sequence[Sequence]): multiple answers to the BFI-2 questionnaire.
        questions (list[str]): BFI-2 item list for a given trait.

    Returns:
        np.ndarray: single trait value per given answer.
    """
    min_value, max_value = 1, 5 # lowest and highest possible scores
    scores = np.stack([_process_answer(answer, questions) for answer in answers])
    mean_trait_values = np.mean(scores, axis=1)
    scaled_trait_values = (mean_trait_values - min_value) / (max_value - min_value)
    return scaled_trait_values


def bfi2(answers: Sequence[Sequence], flip_neurocitism: bool = False) -> dict[str, np.ndarray]:
    """Calculates BFI-2 domain and facet scale values.

    Args:
        answers (Sequence[Sequence]): participants' answers to the BFI-2 questionnaire.
        flip_neurocitism (bool, optional): if True, then Neurocitism is converted to Emotional Stability. Defaults to False.

    Returns:
        dict[str, np.ndarray]: Big Five (OCEAN) and FACET scale values for every answer.
    """
    big_five = list(DOMAIN_SCALES.keys())
    trait_values = np.zeros(shape=(len(answers), len(big_five)), dtype=float)
    for trait_index, trait_name in enumerate(big_five):

        values = bfi2_trait(answers, DOMAIN_SCALES[trait_name])

        if trait_name == 'neurocitism' and flip_neurocitism:
            values = flip_trait_dimension(values)

        trait_values[:, trait_index] = values

    facet_names = list(FACET_SCALES.keys())
    facet_values = np.zeros(shape=(len(answers), len(facet_names)), dtype=float)
    for facet_index, facet_name in enumerate(facet_names):

        values = bfi2_trait(answers, FACET_SCALES[facet_name])

        if facet_name in ['Anxiety', 'Depression', 'Emotional Volatility']:
            values = flip_trait_dimension(values)

        facet_values[:, facet_index] = values

    return {
        'OCEAN': trait_values,
        'FACET': facet_values,
    }


def flip_trait_dimension(single_trait_values: np.ndarray) -> np.ndarray:
    """Flips trait values within the dimension.
    In case of OCEAN, all traits except Neurocitism have negative connotation
    attached to the lower end of the dimension, and positive to the higher end of the dimension.
    Only Neurocitism works the exact opposite.
    For easier further machine learning useage, Neurocitism should be flipped to be similar to the other traits.
    Flipping within scaled dimension is simple, because the values are in range [0..1], and 1-values are the expected result.
    Emotional Stability is the flipped Neurocitism.

    Example:
        Neurocitism value for the participant is 0.7.
        Emotional Stability = 1 - Neurocitism
        Emotional Stability value for the participant is 0.3.

    Args:
        single_trait_values (np.ndarray): trait values of shape (N,).

    Raises:
        ValueError: raises if single_trait_values has more than 1 dimension.
        ValueError: raises if single_trait_values are not in range [0..1].

    Returns:
        np.ndarray: flipped trait values.
    """
    if single_trait_values.ndim > 1:
        raise ValueError(f'Tensor shape expected to be (N,), got instead {single_trait_values.shape}.')

    if single_trait_values.min() < 0 or single_trait_values.max() > 1:
        raise ValueError(f'Tensor values are expected to be in range [0..1], got instead [{single_trait_values.min()}..{single_trait_values.max()}]')

    return 1 - single_trait_values