"""Runtime settings for the data-collection application.

Everything is read from ``PQ_*`` environment variables, so no absolute path is ever
baked into the repository and an operator configures a lab machine without editing
code.

The host default is deliberate: participant self-reports are consent-restricted, and
this application is built for a machine in a lab rather than a service on a network.
Binding to loopback is the safe default, and moving off it is an explicit act.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

__all__ = ["Settings", "settings"]

LOOPBACK = "127.0.0.1"
"""The only address this application binds to unless told otherwise."""


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back on a bad value.

    Args:
        name: Variable name.
        default: Value to use when unset or unparseable.

    Returns:
        The configured integer.
    """
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass(slots=True)
class Settings:
    """Where the application listens and what it writes to.

    Attributes:
        host: Address to bind. Defaults to loopback.
        port: Port to listen on.
        database_url: Record store, or ``None`` to use the package default.
        title: Browser title and header text.
        show: Whether to open a browser on start.
    """

    host: str = field(default_factory=lambda: os.environ.get("PQ_HOST", LOOPBACK))
    port: int = field(default_factory=lambda: _env_int("PQ_PORT", 8080))
    database_url: str | None = field(default_factory=lambda: os.environ.get("PQ_DATABASE_URL"))
    title: str = "Personality Questionnaire"
    show: bool = False

    @property
    def is_loopback(self) -> bool:
        """Whether the configured host keeps the application off the network."""
        return self.host in {LOOPBACK, "localhost", "::1"}

    @property
    def exposure_warning(self) -> str | None:
        """A warning to log when the application is reachable from other machines.

        Returns:
            The warning text, or ``None`` when bound to loopback.
        """
        if self.is_loopback:
            return None
        return (
            f"listening on {self.host}, which is reachable from other machines. "
            "Participant responses are consent-restricted; bind to 127.0.0.1 unless "
            "the network is one you control."
        )


settings = Settings()
"""The process-wide settings instance.

Mutate its fields to change behaviour at runtime without re-importing.
"""
