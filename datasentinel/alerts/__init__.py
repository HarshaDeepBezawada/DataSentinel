"""Alerting modules for SMTP and Slack."""

from datasentinel.alerts.base import BaseAlertNotifier
from datasentinel.alerts.email_notifier import EmailNotifier
from datasentinel.alerts.slack_notifier import SlackNotifier
from datasentinel.alerts.manager import AlertManager

__all__ = [
    "BaseAlertNotifier",
    "EmailNotifier",
    "SlackNotifier",
    "AlertManager",
]
