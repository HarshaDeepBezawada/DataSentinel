"""Abstract BaseConnector for DataSentinel data connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional
import pandas as pd

from datasentinel.core.dataset import DataSet


class BaseConnector(ABC):
    """Abstract base class that all data connectors must implement."""

    def __init__(self, name: str, options: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.options: Dict[str, Any] = options or {}
        self._connected: bool = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection or validate accessibility of the source."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection or release any held resources."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test whether the data source is reachable and valid."""
        pass

    @abstractmethod
    def fetch_data(self) -> DataSet:
        """Fetch and return the data as a unified DataSet."""
        pass

    @abstractmethod
    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        """Stream data in chunks for memory-efficient processing of large sources."""
        pass

    def __enter__(self) -> BaseConnector:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.disconnect()
