"""Base alert notifier interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datasentinel.core.types import PipelineRunResult


class BaseAlertNotifier(ABC):
    """Abstract base class for sending pipeline alerts."""

    @abstractmethod
    def send_alert(self, result: PipelineRunResult) -> bool:
        """Dispatch alert summary for a pipeline run result.

        Must not include raw data rows — only summary counts and top violations.
        """
        pass
