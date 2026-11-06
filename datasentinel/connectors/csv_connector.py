"""CSV data connector."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConnectorError, SourceNotFoundError


@ConnectorRegistry.register("csv")
class CSVConnector(BaseConnector):
    """Adapter for reading comma-separated or delimited text files."""

    def __init__(self, name: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(name, options)
        self.file_path = str(self.options.get("path", ""))
        self.delimiter = str(self.options.get("delimiter", ","))
        self.encoding = str(self.options.get("encoding", "utf-8"))
        self.has_header = self.options.get("header", 0)

        if not self.file_path:
            raise ConnectorError(f"CSVConnector '{name}': 'path' option is required.")

    def connect(self) -> None:
        """Validate that the file exists and is readable."""
        path = Path(self.file_path)
        if not path.is_file():
            raise SourceNotFoundError(
                f"CSV source file not found: '{self.file_path}'",
                details=f"Current working directory: {os.getcwd()}",
            )
        try:
            with open(path, encoding=self.encoding) as f:
                f.read(10)
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Cannot read CSV file '{self.file_path}': {e}") from e

    def disconnect(self) -> None:
        self._connected = False

    def test_connection(self) -> bool:
        try:
            self.connect()
            return True
        except Exception:
            return False

    def fetch_data(self) -> DataSet:
        self.connect()
        try:
            df = pd.read_csv(
                self.file_path,
                sep=self.delimiter,
                encoding=self.encoding,
                header=self.has_header,
            )
            return DataSet(
                name=self.name,
                data=df,
                chunk_supplier=lambda chunk_size: self.stream_chunks(chunk_size),
                total_rows_hint=len(df),
            )
        except Exception as e:
            raise ConnectorError(f"Failed to parse CSV file '{self.file_path}': {e}") from e

    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        self.connect()
        try:
            reader = pd.read_csv(
                self.file_path,
                sep=self.delimiter,
                encoding=self.encoding,
                header=self.has_header,
                chunksize=chunk_size,
            )
            yield from reader
        except Exception as e:
            raise ConnectorError(f"Error streaming chunks from CSV '{self.file_path}': {e}") from e
