"""The demo must never import the Lab application's storage layer.

A stranger's answers on the public Space must have no code path to a database --
not "disabled by a flag," but structurally absent. This walks the demo package's
own source rather than its runtime import graph, so it also catches a database
import guarded behind a function body that happens not to run in this test.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo"

_FORBIDDEN_PREFIXES = (
    "personality_questionnaire.db",
    "personality_questionnaire.core.state",
    "nicegui",
    "sqlalchemy",
)
"""Modules that belong to the Lab application or its storage, never the demo."""


def _imported_modules(source: str) -> set[str]:
    """Collect every module name a source file imports, however it does it."""
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestNoStorageImports(unittest.TestCase):
    """Every module in demo/ is free of storage and Lab-UI imports."""

    def test_every_demo_file_avoids_forbidden_imports(self):
        for path in sorted(DEMO_DIR.glob("*.py")):
            with self.subTest(file=path.name):
                modules = _imported_modules(path.read_text(encoding="utf-8"))
                for module in modules:
                    for forbidden in _FORBIDDEN_PREFIXES:
                        self.assertFalse(
                            module == forbidden or module.startswith(forbidden + "."),
                            f"{path.name} imports {module!r}, which belongs to the Lab app",
                        )

    def test_the_demo_package_actually_has_files(self):
        """A silently-empty glob would make the test above vacuously pass."""
        self.assertGreaterEqual(len(list(DEMO_DIR.glob("*.py"))), 2)


if __name__ == "__main__":
    unittest.main()
