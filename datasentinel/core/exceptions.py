"""Custom exceptions for DataSentinel."""

from typing import Optional


class DataSentinelError(Exception):
    """Base exception for all DataSentinel errors."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConnectorError(DataSentinelError):
    """Raised when a connector fails to initialize, connect, or read data."""
    pass


class ConnectionFailedError(ConnectorError):
    """Raised when an external connection (DB, API) cannot be established."""
    pass


class SourceNotFoundError(ConnectorError):
    """Raised when a specified data source file or endpoint cannot be found."""
    pass


class ConfigurationError(DataSentinelError):
    """Raised when configuration validation fails."""
    pass


class RuleValidationError(DataSentinelError):
    """Raised when rule configuration is invalid."""
    pass


class RuleExecutionError(DataSentinelError):
    """Raised during rule execution failures."""
    pass


class SchemaDriftError(DataSentinelError):
    """Raised when schema drift analysis fails."""
    pass


class AnomalyDetectionError(DataSentinelError):
    """Raised when anomaly detection encounters an error."""
    pass


class ReportGenerationError(DataSentinelError):
    """Raised when HTML or PDF report generation fails."""
    pass


class AlertNotificationError(DataSentinelError):
    """Raised when sending email or Slack webhook alert fails."""
    pass


class StorageError(DataSentinelError):
    """Raised when reading or writing run history fails."""
    pass
