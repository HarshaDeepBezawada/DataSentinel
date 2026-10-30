"""APScheduler integration for recurring automated pipeline validation."""

from __future__ import annotations

import logging
from typing import Callable, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Manages recurring validation runs using APScheduler with overlap prevention."""

    def __init__(self) -> None:
        self.scheduler = BlockingScheduler()

    def schedule_cron(
        self,
        cron_expression: str,
        job_func: Callable[[], None],
        job_id: str = "datasentinel_validation_job",
    ) -> None:
        """Register a cron job ensuring runs never overlap (coalesce=True, max_instances=1)."""
        trigger = CronTrigger.from_crontab(cron_expression)

        # Enforce non-overlapping execution constraint
        self.scheduler.add_job(
            func=job_func,
            trigger=trigger,
            id=job_id,
            coalesce=True,       # Missed runs coalesce into one
            max_instances=1,     # Prevent concurrent overlapping runs
            replace_existing=True,
        )

    def start(self) -> None:
        """Start blocking scheduler loop."""
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self) -> None:
        """Gracefully shut down scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
