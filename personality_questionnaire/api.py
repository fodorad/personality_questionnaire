"""Backwards-compatible entry point for the pre-2.0 console script.

The ``personality-questionnaire`` script has pointed at :func:`main` since 1.1.0.
It now forwards to :mod:`personality_questionnaire.cli.main`, which accepts both the
subcommand form and the old flat flags.
"""

from __future__ import annotations

from personality_questionnaire.cli.main import main, run

__all__ = ["main", "run"]


if __name__ == "__main__":
    run()
