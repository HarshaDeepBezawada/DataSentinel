"""Slack webhook alert notifier."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import httpx

from datasentinel.alerts.base import BaseAlertNotifier
from datasentinel.core.exceptions import AlertNotificationError
from datasentinel.core.types import PipelineRunResult


class SlackNotifier(BaseAlertNotifier):
    """Sends alert summaries to Slack via incoming webhooks."""

    def __init__(
        self,
        webhook_url_env: str = "SLACK_WEBHOOK_URL",
        channel: Optional[str] = None,
    ) -> None:
        self.webhook_url_env = webhook_url_env
        self.channel = channel
        # Sensitive webhook URL read strictly from environment variable
        self.webhook_url = os.getenv(webhook_url_env)

    def _build_slack_payload(self, result: PipelineRunResult) -> Dict[str, Any]:
        """Construct Slack Block Kit payload with summary metrics and top violations."""
        total_rules = result.rules_passed + result.rules_failed + result.rules_warning
        pass_rate = (result.rules_passed / total_rules * 100.0) if total_rules > 0 else 100.0
        total_anomalies = sum(a.total_anomalies for a in result.anomalies)

        status_emoji = "✅" if result.rules_failed == 0 else "🚨"

        blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} DataSentinel Alert: {result.pipeline_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:*\n`{result.overall_status.value.upper()}`"},
                    {"type": "mrkdwn", "text": f"*Pass Rate:*\n*{pass_rate:.1f}%*"},
                    {"type": "mrkdwn", "text": f"*Total Records:*\n{result.total_rows:,}"},
                    {"type": "mrkdwn", "text": f"*Execution Time:*\n{result.duration_ms:.1f} ms"},
                    {"type": "mrkdwn", "text": f"*Failed Rules:*\n*{result.rules_failed}*"},
                    {"type": "mrkdwn", "text": f"*Anomalies:*\n*{total_anomalies}*"},
                ],
            },
            {"type": "divider"},
        ]

        # Add top failed rules summary (strictly without raw data rows)
        failed_rules = [r for r in result.rule_results if not r.passed]
        if failed_rules:
            violation_text = "*Top Rule Violations:*\n"
            for r in failed_rules[:5]:
                violation_text += f"• *{r.rule_id}* (`{r.column}`): {r.failed_rows} failures ({r.failure_rate * 100:.1f}%) — _{r.message}_\n"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": violation_text},
            })

        payload: Dict[str, Any] = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        return payload

    def send_alert(self, result: PipelineRunResult) -> bool:
        if not self.webhook_url:
            raise AlertNotificationError(
                f"Slack webhook URL not found in environment variable '{self.webhook_url_env}'."
            )

        payload = self._build_slack_payload(result)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            raise AlertNotificationError(f"Failed to post Slack alert: {e}") from e
