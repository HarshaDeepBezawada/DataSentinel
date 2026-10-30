"""Tests for email and Slack alert notifiers."""

from unittest.mock import MagicMock, patch
import pytest

from datasentinel.alerts.email_notifier import EmailNotifier
from datasentinel.alerts.manager import AlertManager
from datasentinel.alerts.slack_notifier import SlackNotifier
from datasentinel.core.types import (
    PipelineRunResult,
    RuleResult,
    ValidationStatus,
)
from datasentinel.rules.models import AlertConfig, EmailAlertConfig, SlackAlertConfig


@pytest.fixture
def mock_pipeline_result() -> PipelineRunResult:
    return PipelineRunResult(
        run_id="run-alert-1",
        pipeline_name="Alert Pipeline",
        timestamp="2026-10-30 11:00:00 UTC",
        duration_ms=45.0,
        total_rows=500,
        total_columns=4,
        rules_passed=3,
        rules_failed=1,
        rules_warning=0,
        rule_results=[
            RuleResult(
                rule_id="R1",
                rule_type="null_check",
                column="user_id",
                status=ValidationStatus.FAILED,
                passed=False,
                total_rows=500,
                failed_rows=5,
                failure_rate=0.01,
                sample_failures=[None],
                message="Found 5 null user IDs.",
            )
        ],
        overall_status=ValidationStatus.FAILED,
    )


def test_email_notifier_payload_has_no_raw_data(mock_pipeline_result: PipelineRunResult) -> None:
    """Verify email body includes summary metrics and top violations but NO raw data rows."""
    notifier = EmailNotifier(recipients=["ops@example.com"], smtp_host="localhost")
    body = notifier._build_summary_body(mock_pipeline_result)

    assert "Alert Pipeline" in body
    assert "Pass Rate:      75.0%" in body
    assert "Total Records:  500" in body
    assert "Found 5 null user IDs." in body
    # Confirm no raw rows or tables
    assert "SELECT" not in body
    assert "DataFrame" not in body


def test_email_notifier_send(monkeypatch: pytest.MonkeyPatch, mock_pipeline_result: PipelineRunResult) -> None:
    """Test SMTP client send with mocked smtplib."""
    mock_smtp = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp) as mock_cls:
        notifier = EmailNotifier(recipients=["ops@example.com"], smtp_host="smtp.example.com", smtp_port=587)
        success = notifier.send_alert(mock_pipeline_result)

        assert success is True
        mock_cls.assert_called_once_with("smtp.example.com", 587, timeout=15)
        mock_smtp.__enter__().sendmail.assert_called_once()


def test_slack_notifier_payload_has_no_raw_data(mock_pipeline_result: PipelineRunResult, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Slack Block Kit payload contains only aggregate counts and top violations."""
    monkeypatch.setenv("TEST_SLACK_URL", "https://hooks.slack.com/services/T/B/X")
    notifier = SlackNotifier(webhook_url_env="TEST_SLACK_URL", channel="#alerts")

    payload = notifier._build_slack_payload(mock_pipeline_result)
    assert "blocks" in payload
    assert payload["channel"] == "#alerts"

    # Convert entire payload to string and check
    payload_str = str(payload)
    assert "Alert Pipeline" in payload_str
    assert "Found 5 null user IDs." in payload_str
    assert "DataFrame" not in payload_str


def test_alert_manager(monkeypatch: pytest.MonkeyPatch, mock_pipeline_result: PipelineRunResult) -> None:
    """Test AlertManager orchestrating multiple notifiers."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/dummy")

    cfg = AlertConfig(
        on_failure_only=True,
        email=EmailAlertConfig(enabled=True, recipients=["team@example.com"]),
        slack=SlackAlertConfig(enabled=True),
    )
    manager = AlertManager(cfg)
    assert len(manager.notifiers) == 2

    # Mock each notifier send_alert
    for n in manager.notifiers:
        n.send_alert = MagicMock(return_value=True)  # type: ignore[method-assign]

    manager.dispatch(mock_pipeline_result)
    for n in manager.notifiers:
        n.send_alert.assert_called_once_with(mock_pipeline_result)  # type: ignore[attr-defined]
