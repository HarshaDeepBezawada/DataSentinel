"""Pydantic v2 configuration models for YAML rules and pipelines."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datasentinel.core.types import Severity


class RuleConfig(BaseModel):
    """Configuration for an individual validation rule."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the rule")
    type: str = Field(..., description="Rule type: null_check, unique_check, range, regex, foreign_key")
    column: str = Field(..., description="Target column name")
    description: str | None = Field(None, description="Human-readable description of the rule")
    severity: Severity = Field(Severity.ERROR, description="Violation severity: error or warning")
    params: dict[str, Any] = Field(default_factory=dict, description="Rule-specific parameters")


class NullCheckConfig(BaseModel):
    """Parameters for null checks."""
    model_config = ConfigDict(extra="forbid")

    allow_nulls: bool = False
    max_null_rate: float = Field(0.0, ge=0.0, le=1.0)


class UniqueCheckConfig(BaseModel):
    """Parameters for uniqueness checks."""
    model_config = ConfigDict(extra="forbid")

    min_unique_rate: float = Field(1.0, ge=0.0, le=1.0)


class RangeCheckConfig(BaseModel):
    """Parameters for numeric range checks."""
    model_config = ConfigDict(extra="forbid")

    min_value: float | None = None
    max_value: float | None = None
    inclusive: bool = True

    @field_validator("max_value")
    @classmethod
    def validate_range(cls, v: float | None, info: Any) -> float | None:
        min_v = info.data.get("min_value")
        if min_v is not None and v is not None and min_v > v:
            raise ValueError(f"min_value ({min_v}) cannot be greater than max_value ({v})")
        return v


class RegexCheckConfig(BaseModel):
    """Parameters for regular expression pattern matching."""
    model_config = ConfigDict(extra="forbid")

    pattern: str = Field(..., description="Regex pattern string")
    full_match: bool = True


class ForeignKeyConfig(BaseModel):
    """Parameters for referential integrity checks."""
    model_config = ConfigDict(extra="forbid")

    reference_column: str | None = None
    reference_values: list[Any] | None = None
    reference_dataset: str | None = None


class AnomalyConfig(BaseModel):
    """Configuration for statistical anomaly detection."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    columns: list[str] = Field(default_factory=list)
    method: str = Field("both", pattern="^(zscore|iqr|both)$")
    zscore_threshold: float = Field(3.0, gt=0.0)
    iqr_multiplier: float = Field(1.5, gt=0.0)
    max_anomalies_to_report: int = Field(50, gt=0)


class EmailAlertConfig(BaseModel):
    """SMTP email alert settings."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    recipients: list[str] = Field(default_factory=list)
    smtp_host: str | None = None
    smtp_port: int | None = None
    use_tls: bool = True


class SlackAlertConfig(BaseModel):
    """Slack webhook alert settings."""
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    webhook_url_env: str = "SLACK_WEBHOOK_URL"
    channel: str | None = None


class AlertConfig(BaseModel):
    """Pipeline alerts configuration."""
    model_config = ConfigDict(extra="forbid")

    on_failure_only: bool = True
    email: EmailAlertConfig | None = None
    slack: SlackAlertConfig | None = None


class SourceConfig(BaseModel):
    """Data source configuration."""
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Connector type (csv, excel, json, sqlite, postgresql, rest_api)")
    name: str = "primary"
    options: dict[str, Any] = Field(default_factory=dict)


class BaselineConfig(BaseModel):
    """Schema baseline tracking configuration."""
    model_config = ConfigDict(extra="forbid")

    fingerprint_path: str | None = None
    auto_update: bool = False


class PipelineConfig(BaseModel):
    """Root configuration model for a DataSentinel monitoring pipeline."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Pipeline display name")
    source: SourceConfig
    rules: list[RuleConfig] = Field(default_factory=list)
    schema_baseline: BaselineConfig | None = None
    anomaly_detection: AnomalyConfig | None = None
    alerts: AlertConfig | None = None
