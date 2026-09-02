"""SQLite database utilities for the maintenance intelligence platform."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import pandas as pd


LOGGER = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Raised when database setup or load operations fail."""


class DatabaseManager:
    """Manage SQLite connections, schema creation, and transactional loads."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with production-friendly pragmas enabled."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.execute("PRAGMA synchronous = NORMAL;")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run database statements inside an explicit transaction."""
        connection = self.connect()
        try:
            connection.execute("BEGIN;")
            yield connection
            connection.commit()
        except Exception as exc:
            connection.rollback()
            LOGGER.exception("Database transaction rolled back.")
            raise DatabaseError(f"Database transaction failed: {exc}") from exc
        finally:
            connection.close()

    def initialize_schema(self, ddl_path: str | Path) -> None:
        """Create database tables and indexes from a DDL script."""
        ddl_file = Path(ddl_path)
        if not ddl_file.exists():
            raise FileNotFoundError(f"DDL file not found: {ddl_file}")

        ddl_sql = ddl_file.read_text(encoding="utf-8")
        LOGGER.info("Initializing SQLite schema from %s", ddl_file)

        try:
            with self.connect() as connection:
                connection.executescript(ddl_sql)
        except sqlite3.Error as exc:
            LOGGER.exception("Schema initialization failed.")
            raise DatabaseError(f"Schema initialization failed: {exc}") from exc

    def table_exists(self, table_name: str) -> bool:
        """Return whether a table exists in the SQLite database."""
        query = """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            LIMIT 1;
        """
        with self.connect() as connection:
            result = connection.execute(query, (table_name,)).fetchone()
        return result is not None

    def get_row_count(self, table_name: str) -> int:
        """Return the number of rows in a table."""
        self._validate_identifier(table_name)
        with self.connect() as connection:
            result = connection.execute(f"SELECT COUNT(*) AS row_count FROM {table_name};").fetchone()
        return int(result["row_count"])

    def load_dataframes(
        self,
        table_frames: Mapping[str, pd.DataFrame],
        replace_existing: bool = True,
    ) -> None:
        """Load multiple dataframes into SQLite in one atomic transaction."""
        if not table_frames:
            raise ValueError("No table dataframes were provided for loading.")

        for table_name, dataframe in table_frames.items():
            self._validate_identifier(table_name)
            if dataframe.empty:
                raise ValueError(f"Cannot load empty dataframe into {table_name}.")

        LOGGER.info("Loading %d table(s) into %s", len(table_frames), self.database_path)

        with self.transaction() as connection:
            if replace_existing:
                for table_name in reversed(list(table_frames.keys())):
                    LOGGER.info("Deleting existing rows from %s", table_name)
                    connection.execute(f"DELETE FROM {table_name};")

            for table_name, dataframe in table_frames.items():
                LOGGER.info("Loading %d rows into %s", len(dataframe), table_name)
                dataframe.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists="append",
                    index=False,
                    method="multi",
                    chunksize=1_000,
                )

    def execute_query(
        self,
        query: str,
        parameters: Sequence[object] | None = None,
    ) -> list[sqlite3.Row]:
        """Execute a read query and return all rows."""
        with self.connect() as connection:
            cursor = connection.execute(query, parameters or ())
            return cursor.fetchall()

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if not identifier.replace("_", "").isalnum() or identifier[0].isdigit():
            raise ValueError(f"Unsafe SQLite identifier: {identifier}")

