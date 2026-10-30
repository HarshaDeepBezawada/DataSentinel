"""SQLite-backed run history storage for pipeline execution trends."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from datasentinel.core.exceptions import StorageError
from datasentinel.core.types import PipelineRunResult


class RunHistoryStore:
    """Manages SQLite storage for historical pipeline validation runs."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path(".datasentinel/history.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create history table if it doesn't already exist."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_history (
                        run_id TEXT PRIMARY KEY,
                        pipeline_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        duration_ms REAL NOT NULL,
                        total_rows INTEGER NOT NULL,
                        total_columns INTEGER NOT NULL,
                        rules_passed INTEGER NOT NULL,
                        rules_failed INTEGER NOT NULL,
                        rules_warning INTEGER NOT NULL,
                        anomaly_count INTEGER NOT NULL,
                        drift_count INTEGER NOT NULL,
                        overall_status TEXT NOT NULL,
                        details_json TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pipeline_time ON run_history(pipeline_name, timestamp DESC)"
                )
        except Exception as e:
            raise StorageError(f"Failed to initialize SQLite history store at '{self.db_path}': {e}") from e

    def record_run(self, result: PipelineRunResult) -> None:
        """Insert a pipeline validation run result into history."""
        total_anomalies = sum(a.total_anomalies for a in result.anomalies)
        drift_count = len(result.drift_report.diffs) if result.drift_report else 0

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO run_history (
                        run_id, pipeline_name, timestamp, duration_ms,
                        total_rows, total_columns, rules_passed, rules_failed,
                        rules_warning, anomaly_count, drift_count, overall_status,
                        details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.run_id,
                        result.pipeline_name,
                        result.timestamp,
                        result.duration_ms,
                        result.total_rows,
                        result.total_columns,
                        result.rules_passed,
                        result.rules_failed,
                        result.rules_warning,
                        total_anomalies,
                        drift_count,
                        result.overall_status.value,
                        result.model_dump_json(),
                    ),
                )
        except Exception as e:
            raise StorageError(f"Failed to record run history for '{result.run_id}': {e}") from e

    def get_recent_runs(self, pipeline_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent runs for trend line visualization."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT run_id, pipeline_name, timestamp, duration_ms,
                           total_rows, rules_passed, rules_failed, rules_warning,
                           anomaly_count, drift_count, overall_status
                    FROM run_history
                    WHERE pipeline_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (pipeline_name, limit),
                )
                rows = cursor.fetchall()
                # Return in chronological order (oldest to newest)
                return [dict(r) for r in reversed(rows)]
        except Exception as e:
            raise StorageError(f"Failed to fetch recent runs for '{pipeline_name}': {e}") from e
