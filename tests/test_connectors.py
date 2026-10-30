"""Tests for data connectors and connector registry."""

import json
from pathlib import Path
import sqlite3
import pandas as pd
import pytest
import httpx

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.connectors.csv_connector import CSVConnector
from datasentinel.connectors.excel_connector import ExcelConnector
from datasentinel.connectors.json_connector import JSONConnector
from datasentinel.connectors.sql_connector import SQLConnector
from datasentinel.connectors.api_connector import RestAPIConnector
from datasentinel.core.exceptions import ConnectionFailedError, ConnectorError, SourceNotFoundError


def test_registry_registration() -> None:
    """Test registry discovery and extension."""
    available = ConnectorRegistry.list_available()
    assert "csv" in available
    assert "excel" in available
    assert "json" in available
    assert "sqlite" in available
    assert "rest_api" in available

    with pytest.raises(ConnectorError, match="Unknown data source type"):
        ConnectorRegistry.get("nonexistent_format_xyz")


def test_csv_connector(tmp_path: Path) -> None:
    """Test CSVConnector reading and streaming."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,val\n1,10\n2,20\n3,30", encoding="utf-8")

    connector = CSVConnector(name="test_csv", options={"path": str(csv_file)})
    assert connector.test_connection() is True

    ds = connector.fetch_data()
    assert ds.shape == (3, 2)
    assert list(ds.columns) == ["id", "val"]

    # Stream chunks
    chunks = list(connector.stream_chunks(chunk_size=2))
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 1


def test_csv_connector_missing_file(tmp_path: Path) -> None:
    """Test CSVConnector error handling on missing file."""
    connector = CSVConnector(name="test_csv", options={"path": str(tmp_path / "absent.csv")})
    assert connector.test_connection() is False
    with pytest.raises(SourceNotFoundError):
        connector.fetch_data()


def test_excel_connector(tmp_path: Path) -> None:
    """Test ExcelConnector reading."""
    xlsx_file = tmp_path / "data.xlsx"
    df = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
    df.to_excel(xlsx_file, index=False)

    connector = ExcelConnector(name="test_excel", options={"path": str(xlsx_file)})
    assert connector.test_connection() is True
    ds = connector.fetch_data()
    assert ds.shape == (2, 2)


def test_json_connector_flat(tmp_path: Path) -> None:
    """Test JSONConnector reading flat arrays."""
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]))

    connector = JSONConnector(name="test_json", options={"path": str(json_file)})
    assert connector.test_connection() is True
    ds = connector.fetch_data()
    assert ds.shape == (2, 2)
    assert "name" in ds.columns


def test_json_connector_nested(tmp_path: Path) -> None:
    """Test JSONConnector reading nested path."""
    json_file = tmp_path / "data.json"
    nested_data = {
        "status": "success",
        "data": {
            "records": [
                {"id": 101, "score": 95},
                {"id": 102, "score": 88},
            ]
        }
    }
    json_file.write_text(json.dumps(nested_data))

    connector = JSONConnector(
        name="test_nested_json",
        options={"path": str(json_file), "nested_path": "data.records"},
    )
    ds = connector.fetch_data()
    assert ds.shape == (2, 2)
    assert list(ds.columns) == ["id", "score"]


def test_json_connector_bad_nested_path(tmp_path: Path) -> None:
    """Test JSONConnector when nested path does not exist."""
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps({"wrong": []}))

    connector = JSONConnector(
        name="test_bad_nested",
        options={"path": str(json_file), "nested_path": "data.records"},
    )
    with pytest.raises(ConnectorError, match="Nested path"):
        connector.fetch_data()


def test_sql_connector_sqlite(tmp_path: Path) -> None:
    """Test SQLConnector with SQLite database and table/query."""
    db_file = tmp_path / "app.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE users (id INTEGER, username TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")

    connector = SQLConnector(
        name="test_sqlite",
        options={"connection_url": f"sqlite:///{db_file}", "table": "users"},
    )
    assert connector.test_connection() is True
    ds = connector.fetch_data()
    assert ds.shape == (2, 2)
    assert "username" in ds.columns

    # Test custom query
    connector_query = SQLConnector(
        name="test_query",
        options={
            "connection_url": f"sqlite:///{db_file}",
            "query": "SELECT username FROM users WHERE id = 1",
        },
    )
    ds_query = connector_query.fetch_data()
    assert ds_query.shape == (1, 1)


def test_sql_connector_env_substitution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test sensitive database credentials expanded securely from env vars."""
    db_file = tmp_path / "env.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE items (val TEXT)")
        conn.execute("INSERT INTO items VALUES ('item1')")

    monkeypatch.setenv("SECURE_DB_PATH", str(db_file))
    connector = SQLConnector(
        name="test_env_db",
        options={
            "connection_url": "sqlite:///${SECURE_DB_PATH}",
            "table": "items",
        },
    )
    ds = connector.fetch_data()
    assert ds.shape == (1, 1)


def test_api_connector_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test RestAPIConnector with pagination and headers."""
    monkeypatch.setenv("TEST_API_TOKEN", "secret-token-123")

    fake_records = [{"id": i, "name": f"item_{i}"} for i in range(1, 25)]

    def custom_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer secret-token-123"
        url = str(request.url)
        # Parse page param
        if "page=2" in url:
            return httpx.Response(200, json={"items": fake_records[10:20]})
        elif "page=3" in url:
            return httpx.Response(200, json={"items": fake_records[20:]})
        else:
            return httpx.Response(200, json={"items": fake_records[:10]})

    transport = httpx.MockTransport(custom_handler)

    # Monkeypatch httpx.Client to use mock transport
    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))

    connector = RestAPIConnector(
        name="test_api",
        options={
            "url": "https://api.example.com/v1/records",
            "nested_path": "items",
            "auth": {"token_env": "TEST_API_TOKEN"},
            "pagination": {
                "enabled": True,
                "type": "page",
                "page_param": "page",
                "page_size_param": "limit",
                "page_size": 10,
                "max_pages": 5,
            },
        },
    )

    ds = connector.fetch_data()
    assert ds.shape == (24, 2)
    assert "name" in ds.columns
