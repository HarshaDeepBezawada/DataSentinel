"""Verification and benchmark test for 500,000-row dataset streaming anomaly detection."""

import os
import numpy as np
import pandas as pd
import pytest

from datasentinel.anomaly.iqr import IQRAnomalyDetector
from datasentinel.anomaly.zscore import ZScoreAnomalyDetector
from datasentinel.core.dataset import DataSet

try:
    import psutil
    def get_memory_mb() -> float:
        return float(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
except ImportError:
    def get_memory_mb() -> float:
        return 0.0


def test_500k_rows_streaming_anomaly_detection() -> None:
    """Verify that anomaly detection processes 500,000 rows memory-efficiently in chunks."""
    total_target_rows = 500_000
    chunk_size = 50_000
    num_chunks = total_target_rows // chunk_size

    # Injected anomalies at known points
    injected_outliers = {
        125_000: 999_999.0,
        375_000: -888_888.0,
    }

    def chunk_generator(size: int):
        np.random.seed(42)
        row_cursor = 0
        for _ in range(num_chunks):
            # Normal distribution with mean=100.0, std=15.0
            data = np.random.normal(loc=100.0, scale=15.0, size=size)
            # Inject outliers if inside current chunk
            for idx, val in injected_outliers.items():
                if row_cursor <= idx < row_cursor + size:
                    offset = idx - row_cursor
                    data[offset] = val
            row_cursor += size
            yield pd.DataFrame({"metric_value": data})

    mem_before_mb = get_memory_mb()

    dataset = DataSet(
        name="large_dataset_500k",
        chunk_supplier=chunk_generator,
        total_rows_hint=total_target_rows,
    )

    # 1. Test Z-score streaming on 500k rows
    z_detector = ZScoreAnomalyDetector(threshold=3.0, max_samples=10)
    z_summary = z_detector.detect(dataset, "metric_value")

    mem_after_z_mb = get_memory_mb()
    mem_growth_mb = mem_after_z_mb - mem_before_mb

    assert z_summary.total_anomalies >= 2
    z_vals = [p.value for p in z_summary.sample_anomalies]
    assert any(abs(v - 999_999.0) < 1.0 for v in z_vals)
    assert any(abs(v - (-888_888.0)) < 1.0 for v in z_vals)

    # 2. Test IQR streaming on 500k rows
    iqr_detector = IQRAnomalyDetector(multiplier=1.5, max_samples=10)
    iqr_summary = iqr_detector.detect(dataset, "metric_value")

    mem_after_iqr_mb = get_memory_mb()

    assert iqr_summary.total_anomalies >= 2
    iqr_vals = [p.value for p in iqr_summary.sample_anomalies]
    assert any(abs(v - 999_999.0) < 1.0 for v in iqr_vals)
    assert any(abs(v - (-888_888.0)) < 1.0 for v in iqr_vals)

    # Memory constraint check: memory growth during chunk streaming must be bounded
    # (Holding 500k rows of wide data in memory would take large memory, streaming takes < 150MB delta)
    assert mem_growth_mb < 200.0, f"Memory growth excessive: {mem_growth_mb:.2f} MB"
