"""SMTP email alert notifier."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datasentinel.alerts.base import BaseAlertNotifier
from datasentinel.core.exceptions import AlertNotificationError
from datasentinel.core.types import PipelineRunResult


class EmailNotifier(BaseAlertNotifier):
    """Sends alert emails via SMTP with executive summaries and violation counts."""

    def __init__(
        self,
        recipients: list[str],
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        use_tls: bool = True,
    ) -> None:
        self.recipients = recipients
        self.smtp_host: str = str(smtp_host or os.getenv("SMTP_HOST") or "localhost")
        self.smtp_port: int = int(smtp_port or os.getenv("SMTP_PORT") or 587)
        self.use_tls = use_tls
        # Sensitive credentials read exclusively from environment variables
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def _build_summary_body(self, result: PipelineRunResult) -> str:
        """Construct sanitized summary body containing only aggregate metrics and top rule violations."""
        total_rules = result.rules_passed + result.rules_failed + result.rules_warning
        pass_rate = (result.rules_passed / total_rules * 100.0) if total_rules > 0 else 100.0
        total_anomalies = sum(a.total_anomalies for a in result.anomalies)

        body_lines = [
            f"DataSentinel Pipeline Quality Alert: {result.pipeline_name}",
            "=" * 50,
            f"Overall Status: {result.overall_status.value.upper()}",
            f"Run ID:         {result.run_id}",
            f"Timestamp:      {result.timestamp}",
            f"Execution Time: {result.duration_ms:.2f} ms",
            f"Total Records:  {result.total_rows:,}",
            f"Pass Rate:      {pass_rate:.1f}%",
            f"Rules Passed:   {result.rules_passed}",
            f"Rules Failed:   {result.rules_failed}",
            f"Rules Warning:  {result.rules_warning}",
            f"Total Anomalies:{total_anomalies}",
            "",
            "Top Quality Violations:",
            "-" * 30,
        ]

        failed_rules = [r for r in result.rule_results if not r.passed]
        if not failed_rules:
            body_lines.append("No rule failures recorded.")
        else:
            for r in failed_rules[:5]:
                body_lines.append(
                    f"• [{r.rule_id}] Column '{r.column}' ({r.rule_type}): "
                    f"{r.failed_rows} failures ({r.failure_rate * 100:.1f}%) - {r.message}"
                )

        if result.drift_report and result.drift_report.has_drift:
            body_lines.extend([
                "",
                "Schema Drift:",
                "-" * 30,
                f"• {len(result.drift_report.diffs)} structural changes detected against baseline.",
            ])

        return "\n".join(body_lines)

    def send_alert(self, result: PipelineRunResult) -> bool:
        if not self.recipients:
            return False

        subject = (
            f"[DataSentinel] Alert: Pipeline '{result.pipeline_name}' - "
            f"{result.overall_status.value.upper()} ({result.rules_failed} failed rules)"
        )
        body = self._build_summary_body(result)

        msg = MIMEMultipart()
        msg["From"] = self.smtp_user or "datasentinel@internal.net"
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(msg["From"], self.recipients, msg.as_string())
            return True
        except Exception as e:
            raise AlertNotificationError(f"Failed to send email alert via SMTP: {e}") from e
