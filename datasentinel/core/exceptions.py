"""Custom exceptions for DataSentinel."""



class DataSentinelError(Exception):
    """Base exception for all DataSentinel errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConnectorError(DataSentinelError):
    """Raised when a connector fails to initialize, connect, or read data."""


class ConnectionFailedError(ConnectorError):
    """Raised when an external connection (DB, API) cannot be established."""


class SourceNotFoundError(ConnectorError):
    """Raised when a specified data source file or endpoint cannot be found."""


class ConfigurationError(DataSentinelError):
    """Raised when configuration validation fails."""


class RuleValidationError(DataSentinelError):
    """Raised when rule configuration is invalid."""


class RuleExecutionError(DataSentinelError):
    """Raised during rule execution failures."""


class SchemaDriftError(DataSentinelError):
    """Raised when schema drift analysis fails."""


class AnomalyDetectionError(DataSentinelError):
    """Raised when anomaly detection encounters an error."""


class ReportGenerationError(DataSentinelError):
    """Raised when HTML or PDF report generation fails."""


class AlertNotificationError(DataSentinelError):
    """Raised when sending email or Slack webhook alert fails."""


class StorageError(DataSentinelError):
    """Raised when reading or writing run history fails."""
