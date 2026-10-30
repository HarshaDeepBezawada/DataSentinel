"""Unified DataSet interface for in-memory and chunked streaming data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from datasentinel.core.types import ColumnSchema, SchemaFingerprint


class DataSet:
    """Unified wrapper around tabular data supporting both in-memory and chunked access."""

    def __init__(
        self,
        name: str,
        data: Optional[pd.DataFrame] = None,
        chunk_supplier: Optional[Callable[[int], Iterator[pd.DataFrame]]] = None,
        total_rows_hint: Optional[int] = None,
    ) -> None:
        self.name = name
        self._df: Optional[pd.DataFrame] = data
        self._chunk_supplier = chunk_supplier
        self._total_rows_hint = total_rows_hint

        if self._df is None and self._chunk_supplier is None:
            raise ValueError("DataSet requires either a DataFrame or a chunk_supplier callable")

        if self._df is not None:
            self._columns = list(self._df.columns)
            self._shape = self._df.shape
        else:
            self._columns = []
            self._shape = (self._total_rows_hint or 0, 0)

    @property
    def columns(self) -> List[str]:
        """Return list of column names."""
        if self._df is not None:
            return list(self._df.columns)
        if not self._columns and self._chunk_supplier is not None:
            # Peek at the first chunk to inspect columns
            first_chunk = next(self.iter_chunks(chunk_size=10), None)
            if first_chunk is not None:
                self._columns = list(first_chunk.columns)
        return self._columns

    @property
    def shape(self) -> Tuple[int, int]:
        """Return (rows, cols) shape."""
        if self._df is not None:
            return (int(self._df.shape[0]), int(self._df.shape[1]))
        return (int(self._shape[0]), int(self._shape[1]))

    def to_dataframe(self) -> pd.DataFrame:
        """Return the complete dataset as a pandas DataFrame."""
        if self._df is not None:
            return self._df
        if self._chunk_supplier is not None:
            chunks = list(self._chunk_supplier(50000))
            if chunks:
                self._df = pd.concat(chunks, ignore_index=True)
            else:
                self._df = pd.DataFrame()
            self._shape = self._df.shape
            self._columns = list(self._df.columns)
            return self._df
        return pd.DataFrame()

    def iter_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        """Yield chunks of data to avoid excessive memory usage on large datasets."""
        if self._df is not None:
            num_rows = len(self._df)
            for start in range(0, num_rows, chunk_size):
                yield self._df.iloc[start : start + chunk_size].copy()
        elif self._chunk_supplier is not None:
            yield from self._chunk_supplier(chunk_size)

    def null_counts(self) -> Dict[str, int]:
        """Compute null counts per column efficiently."""
        if self._df is not None:
            return {col: int(self._df[col].isna().sum()) for col in self.columns}
        counts: Dict[str, int] = {col: 0 for col in self.columns}
        for chunk in self.iter_chunks():
            for col in self.columns:
                if col in chunk.columns:
                    counts[col] += int(chunk[col].isna().sum())
        return counts

    def fingerprint(self) -> SchemaFingerprint:
        """Generate a baseline schema fingerprint for schema drift detection."""
        col_schemas: Dict[str, ColumnSchema] = {}
        total_rows = 0

        if self._df is not None:
            total_rows = len(self._df)
            for col in self._df.columns:
                series = self._df[col]
                null_count = int(series.isna().sum())
                unique_count = int(series.nunique(dropna=True))
                dtype_str = str(series.dtype)
                col_schemas[str(col)] = ColumnSchema(
                    name=str(col),
                    dtype=dtype_str,
                    nullable=bool(null_count > 0),
                    null_count=null_count,
                    unique_count=unique_count,
                    total_count=total_rows,
                )
        else:
            # Chunked accumulation for large datasets
            null_accum: Dict[str, int] = {}
            unique_sets: Dict[str, set[Any]] = {}
            dtype_map: Dict[str, str] = {}

            for chunk in self.iter_chunks():
                total_rows += len(chunk)
                for col in chunk.columns:
                    col_str = str(col)
                    if col_str not in null_accum:
                        null_accum[col_str] = 0
                        unique_sets[col_str] = set()
                        dtype_map[col_str] = str(chunk[col].dtype)
                    null_accum[col_str] += int(chunk[col].isna().sum())
                    # Sample unique values if set is not overly large
                    if len(unique_sets[col_str]) < 5000:
                        non_null = chunk[col].dropna()
                        unique_sets[col_str].update(non_null.iloc[:500].tolist())

            for col_name, null_cnt in null_accum.items():
                col_schemas[col_name] = ColumnSchema(
                    name=col_name,
                    dtype=dtype_map.get(col_name, "object"),
                    nullable=bool(null_cnt > 0),
                    null_count=null_cnt,
                    unique_count=len(unique_sets.get(col_name, set())),
                    total_count=total_rows,
                )

        return SchemaFingerprint(
            dataset_name=self.name,
            column_count=len(col_schemas),
            row_count=total_rows,
            columns=col_schemas,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
