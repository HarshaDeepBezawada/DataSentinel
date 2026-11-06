"""Tests for SQLite run history storage and trend analysis."""

from pathlib import Path

from datasentinel.core.types import PipelineRunResult, ValidationStatus
from datasentinel.storage.history import RunHistoryStore


def test_run_history_store(tmp_path: Path) -> None:
    """Test recording runs and retrieving chronological trends."""
    db_file = tmp_path / "test_history.db"
    store = RunHistoryStore(db_path=db_file)

    # Insert 3 successive runs
    for i in range(1, 4):
        run = PipelineRunResult(
            run_id=f"run-{i}",
            pipeline_name="Analytics Pipeline",
            timestamp=f"2026-10-30 10:0{i}:00 UTC",
            duration_ms=50.0 + i,
            total_rows=1000 * i,
            total_columns=5,
            rules_passed=4,
            rules_failed=1 if i == 2 else 0,
            rules_warning=0,
            overall_status=ValidationStatus.FAILED if i == 2 else ValidationStatus.PASSED,
        )
        store.record_run(run)

    # Retrieve trends
    trends = store.get_recent_runs("Analytics Pipeline", limit=10)
    assert len(trends) == 3
    # Chronological: oldest to newest
    assert trends[0]["run_id"] == "run-1"
    assert trends[1]["run_id"] == "run-2"
    assert trends[2]["run_id"] == "run-3"
    assert trends[1]["rules_failed"] == 1
