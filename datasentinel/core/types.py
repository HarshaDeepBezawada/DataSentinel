"""Domain types and Pydantic models for DataSentinel."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Severity level of a rule violation."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(StrEnum):
    """Validation execution status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class DriftType(StrEnum):
    """Types of schema drift detected."""
    ADDED = "added"
    REMOVED = "removed"
    TYPE_CHANGED = "type_changed"
    NULLABILITY_CHANGED = "nullability_changed"


class ColumnSchema(BaseModel):
    """Schema descriptor for a single column."""
    name: str
    dtype: str
    nullable: bool
    null_count: int = 0
    unique_count: int = 0
    total_count: int = 0


class SchemaFingerprint(BaseModel):
    """Fingerprint representing the schema baseline of a dataset."""
    dataset_name: str
    column_count: int
    row_count: int
    columns: dict[str, ColumnSchema]
    generated_at: str


class DriftItem(BaseModel):
    """Individual schema difference item."""
    drift_type: DriftType
    column_name: str
    baseline_value: str | None = None
    current_value: str | None = None
    message: str


class DriftReport(BaseModel):
    """Complete schema drift report comparing current schema against a baseline."""
    baseline_name: str
    current_name: str
    has_drift: bool
    diffs: list[DriftItem] = Field(default_factory=list)
    summary: str = ""


class RuleResult(BaseModel):
    """Result of an individual rule execution."""
    rule_id: str
    rule_type: str
    column: str
    status: ValidationStatus
    passed: bool
    total_rows: int
    failed_rows: int
    failure_rate: float
    sample_failures: list[Any] = Field(default_factory=list)
    message: str
    execution_time_ms: float = 0.0


class AnomalyPoint(BaseModel):
    """An individual anomalous row/cell."""
    column: str
    row_index: int
    value: float
    score: float
    method: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    message: str


class AnomalySummary(BaseModel):
    """Aggregated anomaly statistics for a column."""
    column: str
    method: str
    total_anomalies: int
    anomaly_rate: float
    sample_anomalies: list[AnomalyPoint] = Field(default_factory=list)
    mean: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None


class PipelineRunResult(BaseModel):
    """Overall summary of a pipeline validation run."""
    run_id: str
    pipeline_name: str
    timestamp: str
    duration_ms: float
    total_rows: int
    total_columns: int
    rules_passed: int
    rules_failed: int
    rules_warning: int
    rule_results: list[RuleResult] = Field(default_factory=list)
    drift_report: DriftReport | None = None
    anomalies: list[AnomalySummary] = Field(default_factory=list)
    overall_status: ValidationStatus
