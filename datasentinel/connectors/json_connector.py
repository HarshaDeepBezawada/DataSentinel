"""JSON data connector supporting flat arrays, JSONL, and nested object paths."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConnectorError, SourceNotFoundError


@ConnectorRegistry.register("json")
@ConnectorRegistry.register("jsonl")
class JSONConnector(BaseConnector):
    """Adapter for reading flat or nested JSON / JSONL files."""

    def __init__(self, name: str, options: dict[str, Any] | None = None) -> None:
        super().__init__(name, options)
        self.file_path = str(self.options.get("path", ""))
        self.nested_path = self.options.get("nested_path")  # e.g. "data.records" or "results"
        self.lines = bool(self.options.get("lines", False) or self.file_path.endswith(".jsonl"))

        if not self.file_path:
            raise ConnectorError(f"JSONConnector '{name}': 'path' option is required.")

    def connect(self) -> None:
        path = Path(self.file_path)
        if not path.is_file():
            raise SourceNotFoundError(
                f"JSON source file not found: '{self.file_path}'",
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

    def _extract_nested_path(self, payload: Any, path: str) -> Any:
        """Navigate nested keys via dot-notation (e.g. 'data.items')."""
        current = payload
        parts = path.split(".")
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ConnectorError(
                    f"Nested path '{path}' not found in JSON structure (failed at key '{part}')."
                )
        return current

    def fetch_data(self) -> DataSet:
        self.connect()
        try:
            if self.lines:
                df = pd.read_json(self.file_path, lines=True)
            else:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if self.nested_path:
                    data = self._extract_nested_path(data, self.nested_path)

                if isinstance(data, list):
                    df = pd.json_normalize(data)
                elif isinstance(data, dict):
                    # Single dict or columnar dict
                    df = pd.DataFrame([data])
                else:
                    raise ConnectorError(f"JSON structure must be array or object, got {type(data).__name__}")

            return DataSet(
                name=self.name,
                data=df,
                chunk_supplier=lambda chunk_size: self.stream_chunks(chunk_size),
                total_rows_hint=len(df),
            )
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise ConnectorError(f"Failed to read JSON file '{self.file_path}': {e}") from e

    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        df = self.fetch_data().to_dataframe()
        for start in range(0, len(df), chunk_size):
            yield df.iloc[start : start + chunk_size].copy()
