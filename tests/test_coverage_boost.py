"""Additional targeted tests to maximize test coverage."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import httpx
import pandas as pd
import pytest

from datasentinel.connectors.api_connector import RestAPIConnector
from datasentinel.connectors.sql_connector import SQLConnector
from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConnectionFailedError


def test_dataset_null_counts_and_chunked_fingerprint() -> None:
    """Test null_counts and fingerprint calculation on chunked dataset."""
    df1 = pd.DataFrame({"col_a": [1, None], "col_b": ["x", "y"]})
    df2 = pd.DataFrame({"col_a": [3, 4], "col_b": [None, "z"]})

    def chunk_supplier(chunk_size: int) -> Iterator[pd.DataFrame]:
        yield df1
        yield df2

    ds = DataSet(name="chunked_ds", chunk_supplier=chunk_supplier, total_rows_hint=4)
    nulls = ds.null_counts()
    assert nulls["col_a"] == 1
    assert nulls["col_b"] == 1

    fp = ds.fingerprint()
    assert fp.row_count == 4
    assert fp.column_count == 2
    assert fp.columns["col_a"].nullable is True
    assert fp.columns["col_b"].nullable is True


def test_dataset_to_dataframe_from_chunks() -> None:
    """Test converting chunked DataSet to single DataFrame."""
    def chunk_supplier(chunk_size: int) -> Iterator[pd.DataFrame]:
        yield pd.DataFrame({"a": [1, 2]})
        yield pd.DataFrame({"a": [3, 4]})

    ds = DataSet(name="to_df_test", chunk_supplier=chunk_supplier)
    full_df = ds.to_dataframe()
    assert len(full_df) == 4
    assert list(full_df["a"]) == [1, 2, 3, 4]


def test_sql_connector_stream_chunks_and_errors(tmp_path: Path) -> None:
    """Test SQLConnector streaming chunks and graceful failure messages."""
    db_file = tmp_path / "stream.db"
    conn = sqlite3.connect(db_file)
    try:
        conn.execute("CREATE TABLE records (num INTEGER)")
        conn.executemany("INSERT INTO records VALUES (?)", [(i,) for i in range(10)])
        conn.commit()
    finally:
        conn.close()

    connector = SQLConnector(
        name="sql_stream",
        options={"connection_url": f"sqlite:///{db_file}", "table": "records"},
    )
    chunks = list(connector.stream_chunks(chunk_size=4))
    connector.disconnect()
    assert len(chunks) == 3
    assert len(chunks[0]) == 4
    assert len(chunks[1]) == 4
    assert len(chunks[2]) == 2

    # Test connection failure to invalid database
    bad_conn = SQLConnector(
        name="bad_sql",
        options={"connection_url": "postgresql://invalid_host_12345/nonexistent", "table": "t"},
    )
    with pytest.raises(ConnectionFailedError):
        bad_conn.connect()


def test_api_connector_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test RestAPIConnector graceful error handling on HTTP 500 and network errors."""
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(error_handler)
    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))

    conn = RestAPIConnector(
        name="failing_api",
        options={"url": "https://api.example.com/fail"},
    )
    with pytest.raises(ConnectionFailedError):
        conn.fetch_data()
