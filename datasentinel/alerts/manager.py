"""Alert dispatch manager orchestrating email and Slack notifications."""

from __future__ import annotations

from typing import List, Optional
from datasentinel.alerts.base import BaseAlertNotifier
from datasentinel.alerts.email_notifier import EmailNotifier
from datasentinel.alerts.slack_notifier import SlackNotifier
from datasentinel.core.types import PipelineRunResult, ValidationStatus
from datasentinel.rules.models import AlertConfig


class AlertManager:
    """Coordinates dispatching notifications to all configured channels."""

    def __init__(self, config: Optional[AlertConfig] = None) -> None:
        self.config = config
        self.notifiers: List[BaseAlertNotifier] = []

        if config:
            if config.email and config.email.enabled:
                self.notifiers.append(
                    EmailNotifier(
                        recipients=config.email.recipients,
                        smtp_host=config.email.smtp_host,
                        smtp_port=config.email.smtp_port,
                        use_tls=config.email.use_tls,
                    )
                )
            if config.slack and config.slack.enabled:
                self.notifiers.append(
                    SlackNotifier(
                        webhook_url_env=config.slack.webhook_url_env,
                        channel=config.slack.channel,
                    )
                )

    def dispatch(self, result: PipelineRunResult) -> None:
        """Send notifications to all channels if triggering criteria are met."""
        if not self.config or not self.notifiers:
            return

        # Check if alert should only trigger on failure
        if self.config.on_failure_only and result.overall_status == ValidationStatus.PASSED:
            return

        for notifier in self.notifiers:
            try:
                notifier.send_alert(result)
            except Exception as e:
                # Log error or print warning rather than crashing the pipeline
                print(f"[Warning] Failed to send alert via {type(notifier).__name__}: {e}")
