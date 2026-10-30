"""Statistical anomaly detection orchestrator."""

from __future__ import annotations

from typing import List, Optional
import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from datasentinel.anomaly.iqr import IQRAnomalyDetector
from datasentinel.anomaly.zscore import ZScoreAnomalyDetector
from datasentinel.core.dataset import DataSet
from datasentinel.core.types import AnomalySummary
from datasentinel.rules.models import AnomalyConfig


class StatisticalAnomalyDetector:
    """Orchestrates statistical anomaly detection using Z-score and IQR methods."""

    def __init__(
        self,
        config: AnomalyConfig,
    ) -> None:
        self.config = config
        self.zscore_detector = ZScoreAnomalyDetector(
            threshold=config.zscore_threshold,
            max_samples=config.max_anomalies_to_report,
        )
        self.iqr_detector = IQRAnomalyDetector(
            multiplier=config.iqr_multiplier,
            max_samples=config.max_anomalies_to_report,
        )

    def detect_all(self, dataset: DataSet, show_progress: bool = False) -> List[AnomalySummary]:
        """Detect anomalies across all configured numeric columns."""
        if not self.config.enabled:
            return []

        # Find columns to analyze: if empty, detect numeric columns automatically
        target_columns = self.config.columns
        if not target_columns:
            # Auto-detect numeric columns from dataset
            df_sample = next(dataset.iter_chunks(chunk_size=100), None)
            if df_sample is not None:
                target_columns = [
                    col for col in df_sample.columns
                    if pd.api.types.is_numeric_dtype(df_sample[col])
                ]

        results: List[AnomalySummary] = []
        method = self.config.method.lower()

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[magenta]Running anomaly detection...", total=len(target_columns))
                for col in target_columns:
                    progress.update(task, description=f"[magenta]Analyzing column '{col}'...")
                    if method in ("zscore", "both"):
                        results.append(self.zscore_detector.detect(dataset, col))
                    if method in ("iqr", "both"):
                        results.append(self.iqr_detector.detect(dataset, col))
                    progress.advance(task)
        else:
            for col in target_columns:
                if method in ("zscore", "both"):
                    results.append(self.zscore_detector.detect(dataset, col))
                if method in ("iqr", "both"):
                    results.append(self.iqr_detector.detect(dataset, col))

        return results
