"""SQL database connector supporting PostgreSQL and SQLite via SQLAlchemy 2.0."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterator, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConnectionFailedError, ConnectorError


def _resolve_env_placeholders(val: str) -> str:
    """Expand ${ENV_VAR} or env:VAR_NAME from environment variables."""
    pattern = re.compile(r"\$\{([A-Za-z0-9_]+)\}")

    def repl(m: re.Match[str]) -> str:
        var_name = m.group(1)
        value = os.getenv(var_name)
        if value is None:
            raise ConnectorError(f"Missing required environment variable for database: '{var_name}'")
        return value

    resolved = pattern.sub(repl, val)
    if resolved.startswith("env:"):
        var_name = resolved[4:]
        env_val = os.getenv(var_name)
        if env_val is None:
            raise ConnectorError(f"Missing required environment variable: '{var_name}'")
        return env_val
    return resolved


@ConnectorRegistry.register("sqlite")
@ConnectorRegistry.register("postgresql")
@ConnectorRegistry.register("postgres")
@ConnectorRegistry.register("sql")
class SQLConnector(BaseConnector):
    """Adapter for relational databases (SQLite, PostgreSQL) using SQLAlchemy 2.0."""

    def __init__(self, name: str, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name, options)
        connection_url = str(self.options.get("connection_url") or self.options.get("url", ""))

        # Check for password_env option or environment variable placeholders
        if not connection_url:
            db_type = str(self.options.get("type", "sqlite")).lower()
            if db_type == "sqlite":
                db_path = self.options.get("database", ":memory:")
                connection_url = f"sqlite:///{db_path}"
            elif db_type in ("postgresql", "postgres"):
                user = self.options.get("user", "postgres")
                pwd_env = self.options.get("password_env")
                password = os.getenv(pwd_env) if pwd_env else self.options.get("password", "")
                host = self.options.get("host", "localhost")
                port = self.options.get("port", 5432)
                db_name = self.options.get("database", "postgres")
                connection_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

        if not connection_url:
            raise ConnectorError(f"SQLConnector '{name}': 'connection_url' or DB connection details required.")

        # Expand any ${VAR} syntax in the connection URL
        self.connection_url = _resolve_env_placeholders(connection_url)
        self.table_name = self.options.get("table")
        self.query = self.options.get("query")
        self._engine: Optional[Engine] = None

        if not self.table_name and not self.query:
            raise ConnectorError(
                f"SQLConnector '{name}': either 'table' or 'query' must be specified."
            )

    def connect(self) -> None:
        if self._engine is None:
            try:
                # Configure pooling and timeout for robust connection management
                if self.connection_url.startswith("sqlite"):
                    self._engine = create_engine(self.connection_url)
                else:
                    self._engine = create_engine(
                        self.connection_url,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800,
                    )
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                self._connected = True
            except Exception as e:
                masked_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", self.connection_url)
                raise ConnectionFailedError(
                    f"Failed to connect to database at {masked_url}: {e}"
                ) from e

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
        self._connected = False

    def test_connection(self) -> bool:
        try:
            self.connect()
            return True
        except Exception:
            return False

    def _get_sql_statement(self) -> str:
        if self.query:
            return str(self.query)
        return f"SELECT * FROM {self.table_name}"

    def fetch_data(self) -> DataSet:
        self.connect()
        assert self._engine is not None
        sql = self._get_sql_statement()
        try:
            with self._engine.connect() as conn:
                df = pd.read_sql(text(sql), conn)
            return DataSet(
                name=self.name,
                data=df,
                chunk_supplier=lambda chunk_size: self.stream_chunks(chunk_size),
                total_rows_hint=len(df),
            )
        except Exception as e:
            raise ConnectorError(f"Failed to execute SQL query on '{self.name}': {e}") from e

    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        self.connect()
        assert self._engine is not None
        sql = self._get_sql_statement()
        try:
            with self._engine.connect() as conn:
                for chunk in pd.read_sql(text(sql), conn, chunksize=chunk_size):
                    yield chunk
        except Exception as e:
            raise ConnectorError(f"Failed streaming SQL chunks on '{self.name}': {e}") from e
