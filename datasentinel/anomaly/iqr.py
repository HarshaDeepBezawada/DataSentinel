"""Streaming IQR (Interquartile Range) fence anomaly detector."""

from __future__ import annotations

import random
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import AnomalyPoint, AnomalySummary


class IQRAnomalyDetector:
    """Detects outliers using Interquartile Range (IQR) Tukey fences."""

    def __init__(self, multiplier: float = 1.5, max_samples: int = 50) -> None:
        self.multiplier = multiplier
        self.max_samples = max_samples

    def _compute_quartiles(self, dataset: DataSet, column: str) -> Tuple[float, float, int]:
        """Estimate Q1 and Q3 via reservoir sample or numeric series."""
        sample_buffer: List[float] = []
        max_buffer = 100_000
        total_count = 0

        for chunk in dataset.iter_chunks():
            if column not in chunk.columns:
                continue
            series = pd.to_numeric(chunk[column], errors="coerce").dropna()
            n = len(series)
            if n == 0:
                continue
            total_count += n

            # Reservoir sampling to bound memory if dataset is enormous
            for val in series:
                fval = float(val)
                if len(sample_buffer) < max_buffer:
                    sample_buffer.append(fval)
                else:
                    j = random.randint(0, total_count - 1)
                    if j < max_buffer:
                        sample_buffer[j] = fval

        if total_count < 4 or not sample_buffer:
            return 0.0, 0.0, total_count

        arr = np.array(sample_buffer, dtype=np.float64)
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        return q1, q3, total_count

    def detect(self, dataset: DataSet, column: str) -> AnomalySummary:
        """Second streaming pass: identify records falling outside fences."""
        q1, q3, total_count = self._compute_quartiles(dataset, column)
        iqr = q3 - q1

        if total_count < 4 or iqr == 0.0:
            return AnomalySummary(
                column=column,
                method="iqr",
                total_anomalies=0,
                anomaly_rate=0.0,
                sample_anomalies=[],
                q1=round(q1, 4),
                q3=round(q3, 4),
            )

        lower_fence = q1 - (self.multiplier * iqr)
        upper_fence = q3 + (self.multiplier * iqr)

        anomalies: List[AnomalyPoint] = []
        total_anomalies = 0
        row_offset = 0

        center = (q1 + q3) / 2.0

        for chunk in dataset.iter_chunks():
            if column not in chunk.columns:
                row_offset += len(chunk)
                continue

            series = pd.to_numeric(chunk[column], errors="coerce")
            valid_mask = series.notna()
            vals = series[valid_mask]

            outliers_low = vals[vals < lower_fence]
            outliers_high = vals[vals > upper_fence]

            total_anomalies += len(outliers_low) + len(outliers_high)

            for idx, val in outliers_low.items():
                fval = float(val)
                distance = lower_fence - fval
                conf = min(1.0, 0.5 + 0.5 * (distance / (iqr + 1e-9)))
                point = AnomalyPoint(
                    column=column,
                    row_index=int(idx) if isinstance(idx, int) else row_offset,
                    value=round(fval, 4),
                    score=round(conf, 4),
                    method="iqr",
                    lower_bound=round(lower_fence, 4),
                    upper_bound=round(upper_fence, 4),
                    message=f"Value {fval} below lower fence {lower_fence:.2f} (Q1={q1:.2f}, IQR={iqr:.2f})",
                )
                if len(anomalies) < self.max_samples:
                    anomalies.append(point)
                else:
                    min_idx = min(range(len(anomalies)), key=lambda i: (anomalies[i].score, abs(anomalies[i].value - center)))
                    if (point.score, abs(point.value - center)) > (anomalies[min_idx].score, abs(anomalies[min_idx].value - center)):
                        anomalies[min_idx] = point

            for idx, val in outliers_high.items():
                fval = float(val)
                distance = fval - upper_fence
                conf = min(1.0, 0.5 + 0.5 * (distance / (iqr + 1e-9)))
                point = AnomalyPoint(
                    column=column,
                    row_index=int(idx) if isinstance(idx, int) else row_offset,
                    value=round(fval, 4),
                    score=round(conf, 4),
                    method="iqr",
                    lower_bound=round(lower_fence, 4),
                    upper_bound=round(upper_fence, 4),
                    message=f"Value {fval} above upper fence {upper_fence:.2f} (Q3={q3:.2f}, IQR={iqr:.2f})",
                )
                if len(anomalies) < self.max_samples:
                    anomalies.append(point)
                else:
                    min_idx = min(range(len(anomalies)), key=lambda i: (anomalies[i].score, abs(anomalies[i].value - center)))
                    if (point.score, abs(point.value - center)) > (anomalies[min_idx].score, abs(anomalies[min_idx].value - center)):
                        anomalies[min_idx] = point

            row_offset += len(chunk)

        anomaly_rate = (total_anomalies / total_count) if total_count > 0 else 0.0

        return AnomalySummary(
            column=column,
            method="iqr",
            total_anomalies=total_anomalies,
            anomaly_rate=round(anomaly_rate, 4),
            sample_anomalies=anomalies,
            q1=round(q1, 4),
            q3=round(q3, 4),
        )
