"""Excel data connector."""

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


@ConnectorRegistry.register("excel")
@ConnectorRegistry.register("xlsx")
class ExcelConnector(BaseConnector):
    """Adapter for reading Microsoft Excel files (.xlsx, .xls)."""

    def __init__(self, name: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(name, options)
        self.file_path = str(self.options.get("path", ""))
        self.sheet_name = self.options.get("sheet_name", 0)

        if not self.file_path:
            raise ConnectorError(f"ExcelConnector '{name}': 'path' option is required.")

    def connect(self) -> None:
        path = Path(self.file_path)
        if not path.is_file():
            raise SourceNotFoundError(
                f"Excel source file not found: '{self.file_path}'",
                details=f"Current working directory: {os.getcwd()}",
            )
        self._connected = True

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
            df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            return DataSet(
                name=self.name,
                data=df,
                chunk_supplier=lambda chunk_size: self.stream_chunks(chunk_size),
                total_rows_hint=len(df),
            )
        except Exception as e:
            raise ConnectorError(f"Failed to read Excel file '{self.file_path}': {e}") from e

    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        # Excel is typically loaded in full by openpyxl; we chunk in-memory
        df = self.fetch_data().to_dataframe()
        for start in range(0, len(df), chunk_size):
            yield df.iloc[start : start + chunk_size].copy()
