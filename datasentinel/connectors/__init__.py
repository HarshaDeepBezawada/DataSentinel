"""Connector layer with registry and adapters."""

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.connectors.csv_connector import CSVConnector
from datasentinel.connectors.excel_connector import ExcelConnector
from datasentinel.connectors.json_connector import JSONConnector
from datasentinel.connectors.sql_connector import SQLConnector
from datasentinel.connectors.api_connector import RestAPIConnector

__all__ = [
    "BaseConnector",
    "ConnectorRegistry",
    "CSVConnector",
    "ExcelConnector",
    "JSONConnector",
    "SQLConnector",
    "RestAPIConnector",
]
