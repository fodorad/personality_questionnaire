"""Shipped questionnaire definitions.

Importing this package registers every instrument, so
:data:`personality_questionnaire.registry.REGISTRY` is populated as a side effect of
importing :mod:`personality_questionnaire`. Each module here is pure data; the
arithmetic lives in :mod:`personality_questionnaire.scoring`.
"""

from __future__ import annotations

from personality_questionnaire.instruments.bfi2 import BFI2
from personality_questionnaire.instruments.vasf import VASF

__all__ = ["BFI2", "VASF"]
