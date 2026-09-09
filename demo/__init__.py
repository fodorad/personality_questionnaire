"""A stateless, in-memory demo of the questionnaire form and scoring.

This package must never import :mod:`personality_questionnaire.db`. The Lab
application (``pq ui``) persists to a database on a machine an operator controls;
this one runs as a public Hugging Face Space, where a visitor's answers must never
touch storage at all. ``tests/demo_app/test_isolation.py`` enforces the boundary so it
cannot regress silently.
"""

from __future__ import annotations
