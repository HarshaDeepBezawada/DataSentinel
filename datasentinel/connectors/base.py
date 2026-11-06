"""Abstract BaseConnector for DataSentinel data connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from types import TracebackType
from typing import Any, Self

import pandas as pd

from datasentinel.core.dataset import DataSet


class BaseConnector(ABC):
    """Abstract base class that all data connectors must implement."""

    def __init__(self, name: str, options: dict[str, Any] | None = None) -> None:
        self.name = name
        self.options: dict[str, Any] = options or {}
        self._connected: bool = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection or validate accessibility of the source."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection or release any held resources."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Test whether the data source is reachable and valid."""

    @abstractmethod
    def fetch_data(self) -> DataSet:
        """Fetch and return the data as a unified DataSet."""

    @abstractmethod
    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        """Stream data in chunks for memory-efficient processing of large sources."""

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
