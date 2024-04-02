import numpy as np


# Visual Analogue Scale to Evaluate Fatigue Severity (VAS-F)
VASF_QUESTIONNAIRE: dict[int, str] = {
    1: 'tired',
    2: 'sleepy',
    3: 'drowsy',
    4: 'fatigued',
    5: 'worn out',
    6: 'energetic',
    7: 'active',
    8: 'vigorous',
    9: 'efficient',
    10: 'lively',
    11: 'bushed',
    12: 'exhausted',
    13: 'keeping my eyes open',
    14: 'moving my body',
    15: 'concentrating',
    16: 'carrying on a conversation',
    17: 'desire to close my eyes',
    18: 'desire to lie down',
}


ANSWER_DIMS: dict[int, tuple[str, str]] = {
    1: ('not at all', 'extremely'),
    2: ('not at all', 'extremely'),
    3: ('not at all', 'extremely'),
    4: ('not at all', 'extremely'),
    5: ('not at all', 'extremely'),
    6: ('not at all', 'extremely'),
    7: ('not at all', 'extremely'),
    8: ('not at all', 'extremely'),
    9: ('not at all', 'extremely'),
    10: ('not at all', 'extremely'),
    11: ('not at all', 'totally'),
    12: ('not at all', 'totally'),
    13: ('is no effort at all', 'is a tremendous chore'),
    14: ('is no effort at all', 'is a tremendous chore'),
    15: ('is no effort at all', 'is a tremendous chore'),
    16: ('is no effort at all', 'is a tremendous chore'),
    17: ('I have absolutely no', 'I have a tremendous'),
    18: ('I have absolutely no', 'I have a tremendous'),
}


def vasf(pre_answers: list[int] | np.ndarray, post_answers: list[int] | np.ndarray) -> np.ndarray:
    """Calculate the VAS-F scores based on the answers provided by the participant.

    Args:
        pre_answers (list[int] | np.ndarray): List of answers to the pre-experiment questionnaire.
        post_answers (list[int] | np.ndarray): List of answers to the post-experiment questionnaire.

    Returns:
        np.ndarray: Array containing the relative VAS-F scores for the participant.
    """

    return np.array(post_answers).astype(int) - np.array(pre_answers).astype(int)