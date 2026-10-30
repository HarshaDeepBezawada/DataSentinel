"""Base class for data quality rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any, List, Optional

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import RuleResult, Severity, ValidationStatus


class BaseRule(ABC):
    """Abstract base class for all validation rules."""

    def __init__(
        self,
        rule_id: str,
        rule_type: str,
        column: str,
        description: Optional[str] = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.column = column
        self.description = description
        self.severity = severity

    @abstractmethod
    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, List[Any], str]:
        """Execute the validation logic on the given dataset.

        Returns:
            tuple of (passed, total_rows, failed_rows, sample_failures, message)
        """
        pass

    def evaluate(self, dataset: DataSet) -> RuleResult:
        """Run the rule, measure execution time, and format a standardized RuleResult."""
        start_time = time.perf_counter()

        # Check if column exists in dataset
        if self.column not in dataset.columns:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RuleResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                column=self.column,
                status=ValidationStatus.ERROR,
                passed=False,
                total_rows=0,
                failed_rows=0,
                failure_rate=1.0,
                sample_failures=[],
                message=f"Column '{self.column}' does not exist in dataset (available: {', '.join(dataset.columns)})",
                execution_time_ms=round(elapsed_ms, 2),
            )

        passed, total_rows, failed_rows, sample_failures, message = self.run_check(dataset)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        failure_rate = (failed_rows / total_rows) if total_rows > 0 else 0.0

        if passed:
            status = ValidationStatus.PASSED
        elif self.severity == Severity.WARNING:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED

        return RuleResult(
            rule_id=self.rule_id,
            rule_type=self.rule_type,
            column=self.column,
            status=status,
            passed=passed,
            total_rows=total_rows,
            failed_rows=failed_rows,
            failure_rate=round(failure_rate, 4),
            sample_failures=sample_failures[:10],
            message=message,
            execution_time_ms=round(elapsed_ms, 2),
        )
