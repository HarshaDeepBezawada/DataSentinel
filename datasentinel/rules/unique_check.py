"""Uniqueness validation rule."""

from __future__ import annotations

from typing import Any

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import Severity
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import RuleConfig, UniqueCheckConfig
from datasentinel.rules.registry import RuleRegistry


@RuleRegistry.register("unique_check")
@RuleRegistry.register("unique")
class UniqueCheckRule(BaseRule):
    """Rule verifying that values in a column are sufficiently unique."""

    def __init__(
        self,
        rule_id: str,
        column: str,
        min_unique_rate: float = 1.0,
        description: str | None = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            rule_type="unique_check",
            column=column,
            description=description,
            severity=severity,
        )
        self.min_unique_rate = min_unique_rate

    @classmethod
    def from_config(cls, config: RuleConfig) -> UniqueCheckRule:
        params = UniqueCheckConfig(**config.params)
        return cls(
            rule_id=config.id,
            column=config.column,
            min_unique_rate=params.min_unique_rate,
            description=config.description,
            severity=config.severity,
        )

    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, list[Any], str]:
        df = dataset.to_dataframe()
        total_rows = len(df)
        if total_rows == 0:
            return True, 0, 0, [], "Dataset is empty."

        series = df[self.column].dropna()
        non_null_count = len(series)
        if non_null_count == 0:
            return True, total_rows, 0, [], "All values are null."

        duplicated_mask = series.duplicated(keep=False)
        duplicate_rows = int(duplicated_mask.sum())
        unique_count = int(series.nunique())
        unique_rate = unique_count / non_null_count

        passed = unique_rate >= self.min_unique_rate

        samples: list[Any] = series[duplicated_mask].head(5).tolist()

        if passed:
            msg = (
                f"Column '{self.column}' uniqueness rate {unique_rate:.2%} meets requirement ({self.min_unique_rate:.2%})."
            )
        else:
            msg = (
                f"Column '{self.column}' uniqueness rate {unique_rate:.2%} is below required {self.min_unique_rate:.2%}. "
                f"Found {duplicate_rows} non-unique rows ({len(set(samples))} duplicate sample values: {samples})."
            )

        return passed, total_rows, duplicate_rows, samples, msg
