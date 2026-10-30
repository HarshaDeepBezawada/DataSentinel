"""Tests for APScheduler integration and overlap prevention."""

from unittest.mock import MagicMock
import pytest

from datasentinel.scheduler.runner import PipelineScheduler


def test_scheduler_overlap_prevention() -> None:
    """Verify scheduler registers jobs with coalesce=True and max_instances=1."""
    scheduler = PipelineScheduler()
    dummy_job = MagicMock()

    scheduler.schedule_cron("*/15 * * * *", dummy_job, job_id="test_job")

    job = scheduler.scheduler.get_job("test_job")
    assert job is not None
    assert job.coalesce is True
    assert job.max_instances == 1


def test_scheduler_stop() -> None:
    """Test scheduler shutdown when not running or running."""
    scheduler = PipelineScheduler()
    scheduler.stop()  # Should not raise any error
