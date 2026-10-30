"""Numeric range validation rule."""

from __future__ import annotations

from typing import Any, List, Optional
import pandas as pd

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import Severity
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import RangeCheckConfig, RuleConfig
from datasentinel.rules.registry import RuleRegistry


@RuleRegistry.register("range")
@RuleRegistry.register("range_check")
class RangeCheckRule(BaseRule):
    """Rule verifying that numeric column values fall within a specified [min, max] range."""

    def __init__(
        self,
        rule_id: str,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        inclusive: bool = True,
        description: Optional[str] = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            rule_type="range",
            column=column,
            description=description,
            severity=severity,
        )
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive

    @classmethod
    def from_config(cls, config: RuleConfig) -> RangeCheckRule:
        params = RangeCheckConfig(**config.params)
        return cls(
            rule_id=config.id,
            column=config.column,
            min_value=params.min_value,
            max_value=params.max_value,
            inclusive=params.inclusive,
            description=config.description,
            severity=config.severity,
        )

    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, List[Any], str]:
        total_rows = 0
        failed_count = 0
        samples: List[Any] = []

        for chunk in dataset.iter_chunks():
            total_rows += len(chunk)
            series = pd.to_numeric(chunk[self.column], errors="coerce").dropna()

            if self.inclusive:
                cond = pd.Series(True, index=series.index)
                if self.min_value is not None:
                    cond &= series >= self.min_value
                if self.max_value is not None:
                    cond &= series <= self.max_value
            else:
                cond = pd.Series(True, index=series.index)
                if self.min_value is not None:
                    cond &= series > self.min_value
                if self.max_value is not None:
                    cond &= series < self.max_value

            violators = series[~cond]
            failed_count += len(violators)
            if len(samples) < 5 and len(violators) > 0:
                samples.extend(violators.head(5 - len(samples)).tolist())

        if total_rows == 0:
            return True, 0, 0, [], "Dataset is empty."

        passed = failed_count == 0

        bounds_str = []
        if self.min_value is not None:
            bounds_str.append(f">= {self.min_value}" if self.inclusive else f"> {self.min_value}")
        if self.max_value is not None:
            bounds_str.append(f"<= {self.max_value}" if self.inclusive else f"< {self.max_value}")
        req_desc = " and ".join(bounds_str) or "any"

        if passed:
            msg = f"All values in '{self.column}' satisfy range requirement ({req_desc})."
        else:
            msg = (
                f"Column '{self.column}' has {failed_count} values outside range ({req_desc}). "
                f"Sample violations: {samples}."
            )

        return passed, total_rows, failed_count, samples, msg
