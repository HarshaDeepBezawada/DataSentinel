"""Connector registry implementing the Open/Closed Principle."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from datasentinel.connectors.base import BaseConnector
from datasentinel.core.exceptions import ConnectorError


class ConnectorRegistry:
    """Registry maintaining available data connector implementations."""

    _connectors: ClassVar[dict[str, type[BaseConnector]]] = {}

    @classmethod
    def register(cls, source_type: str) -> Callable[[type[BaseConnector]], type[BaseConnector]]:
        """Decorator to register a connector for a given source type identifier."""
        def decorator(connector_cls: type[BaseConnector]) -> type[BaseConnector]:
            cls._connectors[source_type.lower()] = connector_cls
            return connector_cls
        return decorator

    @classmethod
    def register_connector(cls, source_type: str, connector_cls: type[BaseConnector]) -> None:
        """Register a connector class programmatically."""
        cls._connectors[source_type.lower()] = connector_cls

    @classmethod
    def get(cls, source_type: str) -> type[BaseConnector]:
        """Retrieve the connector class for a source type."""
        source_key = source_type.lower()
        if source_key not in cls._connectors:
            available = ", ".join(sorted(cls._connectors.keys()))
            raise ConnectorError(
                f"Unknown data source type: '{source_type}'. "
                f"Available registered connector types: [{available}]"
            )
        return cls._connectors[source_key]

    @classmethod
    def create(cls, source_type: str, name: str, options: dict[str, Any] | None = None) -> BaseConnector:
        """Instantiate a connector by type."""
        connector_cls = cls.get(source_type)
        return connector_cls(name=name, options=options or {})

    @classmethod
    def list_available(cls) -> list[str]:
        """Return list of all registered source types."""
        return sorted(cls._connectors.keys())
