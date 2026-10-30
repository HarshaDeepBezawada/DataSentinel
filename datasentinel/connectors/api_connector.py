"""REST API data connector with pagination and secure credential management."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterator, List, Optional
import httpx
import pandas as pd

from datasentinel.connectors.base import BaseConnector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConnectionFailedError, ConnectorError


@ConnectorRegistry.register("rest_api")
@ConnectorRegistry.register("api")
@ConnectorRegistry.register("http")
class RestAPIConnector(BaseConnector):
    """Adapter for fetching data from REST APIs with pagination support."""

    def __init__(self, name: str, options: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(name, options)
        self.endpoint_url = str(self.options.get("url") or self.options.get("endpoint", ""))
        if not self.endpoint_url:
            raise ConnectorError(f"RestAPIConnector '{name}': 'url' is required.")

        self.method = str(self.options.get("method", "GET")).upper()
        self.headers: Dict[str, str] = dict(self.options.get("headers", {}))
        self.params: Dict[str, Any] = dict(self.options.get("params", {}))
        self.nested_path = self.options.get("nested_path")  # Path to data array, e.g. "data" or "results"
        self.timeout = float(self.options.get("timeout", 30.0))

        # Pagination config
        pagination = self.options.get("pagination", {})
        self.paginated = bool(pagination.get("enabled", False))
        self.pagination_type = pagination.get("type", "page")  # "page" or "offset" or "link"
        self.page_param = pagination.get("page_param", "page")
        self.page_size_param = pagination.get("page_size_param", "limit")
        self.page_size = int(pagination.get("page_size", 100))
        self.max_pages = int(pagination.get("max_pages", 50))

        # Secure token resolution from environment
        auth_cfg = self.options.get("auth", {})
        token_env = auth_cfg.get("token_env")
        api_key_env = auth_cfg.get("api_key_env")

        if token_env:
            token = os.getenv(token_env)
            if not token:
                raise ConnectorError(f"Environment variable '{token_env}' for auth token is not set.")
            self.headers["Authorization"] = f"Bearer {token}"
        elif api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                raise ConnectorError(f"Environment variable '{api_key_env}' for API key is not set.")
            header_name = auth_cfg.get("header_name", "X-API-Key")
            self.headers[header_name] = api_key

    def connect(self) -> None:
        # Validate URL format
        if not re.match(r"^https?://", self.endpoint_url):
            raise ConnectorError(f"Invalid API endpoint URL: '{self.endpoint_url}'")
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def test_connection(self) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.request(
                    self.method,
                    self.endpoint_url,
                    headers=self.headers,
                    params={**self.params, self.page_size_param: 1} if self.paginated else self.params,
                )
                return resp.status_code < 400
        except Exception:
            return False

    def _extract_items(self, response_data: Any) -> List[Dict[str, Any]]:
        """Navigate nested keys to locate the items array."""
        data = response_data
        if self.nested_path:
            parts = str(self.nested_path).split(".")
            for part in parts:
                if isinstance(data, dict) and part in data:
                    data = data[part]
                else:
                    raise ConnectorError(
                        f"Nested path '{self.nested_path}' not found in API response (at '{part}')."
                    )

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def fetch_data(self) -> DataSet:
        self.connect()
        all_records: List[Dict[str, Any]] = []

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if not self.paginated:
                    resp = client.request(
                        self.method,
                        self.endpoint_url,
                        headers=self.headers,
                        params=self.params,
                    )
                    resp.raise_for_status()
                    all_records = self._extract_items(resp.json())
                else:
                    current_page = 1
                    current_offset = 0

                    for _ in range(self.max_pages):
                        page_params = dict(self.params)
                        if self.pagination_type == "page":
                            page_params[self.page_param] = current_page
                            page_params[self.page_size_param] = self.page_size
                        elif self.pagination_type == "offset":
                            page_params[self.page_param] = current_offset
                            page_params[self.page_size_param] = self.page_size

                        resp = client.request(
                            self.method,
                            self.endpoint_url,
                            headers=self.headers,
                            params=page_params,
                        )
                        resp.raise_for_status()
                        items = self._extract_items(resp.json())
                        if not items:
                            break

                        all_records.extend(items)
                        if len(items) < self.page_size:
                            break

                        current_page += 1
                        current_offset += len(items)

        except httpx.HTTPStatusError as e:
            raise ConnectionFailedError(
                f"API request failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise ConnectionFailedError(f"API network request failed: {e}") from e
        except Exception as e:
            if isinstance(e, ConnectorError):
                raise
            raise ConnectorError(f"Failed to fetch data from API '{self.endpoint_url}': {e}") from e

        df = pd.DataFrame(all_records)
        return DataSet(
            name=self.name,
            data=df,
            chunk_supplier=lambda chunk_size: self.stream_chunks(chunk_size),
            total_rows_hint=len(df),
        )

    def stream_chunks(self, chunk_size: int = 50000) -> Iterator[pd.DataFrame]:
        df = self.fetch_data().to_dataframe()
        for start in range(0, len(df), chunk_size):
            yield df.iloc[start : start + chunk_size].copy()
