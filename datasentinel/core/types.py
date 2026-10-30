"""Domain types and Pydantic models for DataSentinel."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level of a rule violation."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(str, Enum):
    """Validation execution status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class DriftType(str, Enum):
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
    columns: Dict[str, ColumnSchema]
    generated_at: str


class DriftItem(BaseModel):
    """Individual schema difference item."""
    drift_type: DriftType
    column_name: str
    baseline_value: Optional[str] = None
    current_value: Optional[str] = None
    message: str


class DriftReport(BaseModel):
    """Complete schema drift report comparing current schema against a baseline."""
    baseline_name: str
    current_name: str
    has_drift: bool
    diffs: List[DriftItem] = Field(default_factory=list)
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
    sample_failures: List[Any] = Field(default_factory=list)
    message: str
    execution_time_ms: float = 0.0


class AnomalyPoint(BaseModel):
    """An individual anomalous row/cell."""
    column: str
    row_index: int
    value: float
    score: float
    method: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    message: str


class AnomalySummary(BaseModel):
    """Aggregated anomaly statistics for a column."""
    column: str
    method: str
    total_anomalies: int
    anomaly_rate: float
    sample_anomalies: List[AnomalyPoint] = Field(default_factory=list)
    mean: Optional[float] = None
    std: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None


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
    rule_results: List[RuleResult] = Field(default_factory=list)
    drift_report: Optional[DriftReport] = None
    anomalies: List[AnomalySummary] = Field(default_factory=list)
    overall_status: ValidationStatus
