"""Pytest fixtures for DataSentinel test suite."""

import os
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from datasentinel.core.dataset import DataSet


@pytest.fixture
def sample_orders_df() -> pd.DataFrame:
    """Fixture providing clean and dirty e-commerce order records."""
    return pd.DataFrame({
        "order_id": ["ORD-1", "ORD-2", "ORD-3", "ORD-4", "ORD-1"],
        "customer_email": ["alice@corp.com", "bob@corp.com", None, "david@bademail", "eve@corp.com"],
        "total_amount": [100.0, 250.0, -10.0, 99999.0, 150.0],
        "status": ["completed", "shipped", "pending", "completed", "cancelled"],
        "payment_method": ["credit_card", "paypal", "bitcoin", "credit_card", "apple_pay"],
    })


@pytest.fixture
def sample_orders_dataset(sample_orders_df: pd.DataFrame) -> DataSet:
    """Fixture wrapping sample DataFrame in unified DataSet."""
    return DataSet(name="test_orders", data=sample_orders_df)


@pytest.fixture
def clean_numeric_df() -> pd.DataFrame:
    """Fixture providing normally distributed numeric records without outliers."""
    import numpy as np
    np.random.seed(42)
    values = np.random.normal(loc=100.0, scale=10.0, size=200)
    return pd.DataFrame({"metric": values})


@pytest.fixture
def dirty_numeric_df() -> pd.DataFrame:
    """Fixture providing numeric records with known injected outliers."""
    values = [100.0] * 50 + [102.0] * 40 + [98.0] * 40 + [10000.0, -5000.0]
    return pd.DataFrame({"metric": values})


@pytest.fixture
def temp_workspace() -> Path:
    """Fixture providing an isolated temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
