"""Tests that the schema is portable to MySQL.

The claim in the README is that MySQL is a supported backend. These tests keep that
claim honest without a server or a driver: the DDL is compiled against the MySQL
dialect, which is where the differences that matter -- unbounded strings on indexed
columns above all -- would surface.
"""

from __future__ import annotations

import unittest

from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateTable

from personality_questionnaire.db.models import Base


class TestMysqlPortability(unittest.TestCase):
    """Every table compiles under MySQL."""

    def test_every_table_compiles(self):
        for name, table in Base.metadata.tables.items():
            with self.subTest(table=name):
                CreateTable(table).compile(dialect=mysql.dialect())

    def test_indexed_string_columns_have_a_length(self):
        """MySQL refuses to index a column with no declared length."""
        for name, table in Base.metadata.tables.items():
            for column in table.columns:
                indexed = column.index or column.primary_key or column.unique
                if not indexed or not hasattr(column.type, "length"):
                    continue
                with self.subTest(table=name, column=column.name):
                    self.assertIsNotNone(column.type.length)

    def test_constrained_string_columns_have_a_length(self):
        """Columns in a unique constraint are indexed too."""
        for name, table in Base.metadata.tables.items():
            constrained = {
                column.name for constraint in table.constraints for column in constraint.columns
            }
            for column in table.columns:
                if column.name not in constrained or not hasattr(column.type, "length"):
                    continue
                with self.subTest(table=name, column=column.name):
                    self.assertIsNotNone(column.type.length)


class TestOtherDialects(unittest.TestCase):
    """The schema uses no backend-specific construct."""

    def test_compiles_under_sqlite(self):
        for table in Base.metadata.tables.values():
            CreateTable(table).compile(dialect=sqlite.dialect())

    def test_compiles_under_postgresql(self):
        """Not a supported backend, but a useful check that nothing is SQLite-only."""
        for table in Base.metadata.tables.values():
            CreateTable(table).compile(dialect=postgresql.dialect())


if __name__ == "__main__":
    unittest.main()
