"""Tests for statistical anomaly detection (Z-Score and IQR)."""

import pandas as pd
import pytest

from datasentinel.anomaly.detector import StatisticalAnomalyDetector
from datasentinel.anomaly.iqr import IQRAnomalyDetector
from datasentinel.anomaly.zscore import ZScoreAnomalyDetector
from datasentinel.core.dataset import DataSet
from datasentinel.rules.models import AnomalyConfig


def test_zscore_detector(dirty_numeric_df: pd.DataFrame) -> None:
    """Test Z-score outlier detection and confidence scoring."""
    ds = DataSet("dirty_data", data=dirty_numeric_df)
    detector = ZScoreAnomalyDetector(threshold=3.0)
    summary = detector.detect(ds, "metric")

    assert summary.total_anomalies >= 2
    assert summary.anomaly_rate > 0.0
    assert summary.mean is not None
    assert summary.std is not None

    # Check detected sample outliers
    outlier_vals = [p.value for p in summary.sample_anomalies]
    assert 10000.0 in outlier_vals or -5000.0 in outlier_vals

    # Check confidence scores are bounded in [0.5, 1.0]
    for p in summary.sample_anomalies:
        assert 0.5 <= p.score <= 1.0


def test_iqr_detector(dirty_numeric_df: pd.DataFrame) -> None:
    """Test IQR Tukey fence outlier detection."""
    ds = DataSet("dirty_data", data=dirty_numeric_df)
    detector = IQRAnomalyDetector(multiplier=1.5)
    summary = detector.detect(ds, "metric")

    assert summary.total_anomalies >= 2
    assert summary.q1 is not None
    assert summary.q3 is not None

    outlier_vals = [p.value for p in summary.sample_anomalies]
    assert 10000.0 in outlier_vals or -5000.0 in outlier_vals


def test_statistical_anomaly_detector_orchestrator(dirty_numeric_df: pd.DataFrame) -> None:
    """Test orchestrating both Z-Score and IQR on multiple columns."""
    ds = DataSet("dirty_data", data=dirty_numeric_df)
    config = AnomalyConfig(
        enabled=True,
        columns=["metric"],
        method="both",
        zscore_threshold=3.0,
        iqr_multiplier=1.5,
    )
    detector = StatisticalAnomalyDetector(config)
    results = detector.detect_all(ds, show_progress=False)

    assert len(results) == 2  # 1 zscore + 1 iqr
    methods = {r.method for r in results}
    assert "zscore" in methods
    assert "iqr" in methods


def test_chunked_streaming_anomaly_detection() -> None:
    """Test anomaly detection operates on chunked streams without loading full data at once."""
    def chunk_supplier(chunk_size: int):
        for i in range(5):
            if i == 4:
                yield pd.DataFrame({"val": [10.0] * 100 + [99999.0]})
            else:
                yield pd.DataFrame({"val": [10.0] * 100})

    ds = DataSet(name="stream_ds", chunk_supplier=chunk_supplier, total_rows_hint=501)
    detector = ZScoreAnomalyDetector(threshold=3.0)
    summary = detector.detect(ds, "val")

    assert summary.total_anomalies >= 1
    sample_vals = [p.value for p in summary.sample_anomalies]
    assert 99999.0 in sample_vals
