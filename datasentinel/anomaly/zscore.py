"""Streaming Z-score statistical anomaly detector."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import pandas as pd

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import AnomalyPoint, AnomalySummary


class ZScoreAnomalyDetector:
    """Detects statistical outliers using standard score (|z| > threshold)."""

    def __init__(self, threshold: float = 3.0, max_samples: int = 50) -> None:
        self.threshold = threshold
        self.max_samples = max_samples

    def _compute_mean_and_std(self, dataset: DataSet, column: str) -> Tuple[float, float, int]:
        """First streaming pass: compute population mean and sample standard deviation (Welford/sum)."""
        count = 0
        sum_x = 0.0
        sum_sq = 0.0

        for chunk in dataset.iter_chunks():
            if column not in chunk.columns:
                continue
            series = pd.to_numeric(chunk[column], errors="coerce").dropna()
            n = len(series)
            if n == 0:
                continue
            count += n
            sum_x += float(series.sum())
            sum_sq += float((series * series).sum())

        if count < 2:
            return 0.0, 0.0, count

        mean = sum_x / count
        variance = (sum_sq - (sum_x * sum_x) / count) / (count - 1)
        std = math.sqrt(max(0.0, variance))
        return mean, std, count

    def detect(self, dataset: DataSet, column: str) -> AnomalySummary:
        """Second streaming pass: flag rows whose |z| exceeds threshold and score them."""
        mean, std, total_count = self._compute_mean_and_std(dataset, column)

        if total_count < 2 or std == 0.0:
            return AnomalySummary(
                column=column,
                method="zscore",
                total_anomalies=0,
                anomaly_rate=0.0,
                sample_anomalies=[],
                mean=round(mean, 4),
                std=round(std, 4),
            )

        anomalies: List[AnomalyPoint] = []
        total_anomalies = 0
        row_offset = 0

        lower_bound = mean - (self.threshold * std)
        upper_bound = mean + (self.threshold * std)

        for chunk in dataset.iter_chunks():
            if column not in chunk.columns:
                row_offset += len(chunk)
                continue

            series = pd.to_numeric(chunk[column], errors="coerce")
            valid_mask = series.notna()

            # Compute z-scores for valid numeric values
            z_scores = (series[valid_mask] - mean) / std
            outlier_mask = z_scores.abs() > self.threshold

            outlier_indices = series[valid_mask][outlier_mask].index
            total_anomalies += len(outlier_indices)

            for idx in outlier_indices:
                val = float(series.loc[idx])
                z = float(z_scores.loc[idx])
                # Confidence score scales from 0.5 at threshold to 1.0 at 1.5x threshold
                conf = min(1.0, 0.5 + 0.5 * (abs(z) - self.threshold) / max(0.5, self.threshold * 0.5))
                point = AnomalyPoint(
                    column=column,
                    row_index=int(idx) if isinstance(idx, int) else row_offset,
                    value=round(val, 4),
                    score=round(conf, 4),
                    method="zscore",
                    lower_bound=round(lower_bound, 4),
                    upper_bound=round(upper_bound, 4),
                    message=f"Value {val} has Z-score of {z:.2f} (threshold: > {self.threshold})",
                )
                if len(anomalies) < self.max_samples:
                    anomalies.append(point)
                else:
                    min_idx = min(range(len(anomalies)), key=lambda i: (anomalies[i].score, abs(anomalies[i].value - mean)))
                    if (point.score, abs(point.value - mean)) > (anomalies[min_idx].score, abs(anomalies[min_idx].value - mean)):
                        anomalies[min_idx] = point

            row_offset += len(chunk)

        anomaly_rate = (total_anomalies / total_count) if total_count > 0 else 0.0

        return AnomalySummary(
            column=column,
            method="zscore",
            total_anomalies=total_anomalies,
            anomaly_rate=round(anomaly_rate, 4),
            sample_anomalies=anomalies,
            mean=round(mean, 4),
            std=round(std, 4),
        )
