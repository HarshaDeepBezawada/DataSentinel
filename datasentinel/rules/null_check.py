"""Null check validation rule."""

from __future__ import annotations

from typing import Any

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import Severity
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import NullCheckConfig, RuleConfig
from datasentinel.rules.registry import RuleRegistry


@RuleRegistry.register("null_check")
@RuleRegistry.register("not_null")
class NullCheckRule(BaseRule):
    """Rule verifying that a column satisfies null rate and existence constraints."""

    def __init__(
        self,
        rule_id: str,
        column: str,
        allow_nulls: bool = False,
        max_null_rate: float = 0.0,
        description: str | None = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            rule_type="null_check",
            column=column,
            description=description,
            severity=severity,
        )
        self.allow_nulls = allow_nulls
        self.max_null_rate = max_null_rate

    @classmethod
    def from_config(cls, config: RuleConfig) -> NullCheckRule:
        params = NullCheckConfig(**config.params)
        return cls(
            rule_id=config.id,
            column=config.column,
            allow_nulls=params.allow_nulls,
            max_null_rate=params.max_null_rate,
            description=config.description,
            severity=config.severity,
        )

    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, list[Any], str]:
        total_rows = 0
        null_count = 0

        for chunk in dataset.iter_chunks():
            total_rows += len(chunk)
            null_count += int(chunk[self.column].isna().sum())

        if total_rows == 0:
            return True, 0, 0, [], "Dataset is empty."

        actual_null_rate = null_count / total_rows

        if not self.allow_nulls:
            passed = null_count == 0
            msg = (
                f"Column '{self.column}' has {null_count} null values ({actual_null_rate:.2%}); expected 0."
                if not passed
                else f"Column '{self.column}' has zero null values as required."
            )
        else:
            passed = actual_null_rate <= self.max_null_rate
            msg = (
                f"Column '{self.column}' null rate {actual_null_rate:.2%} exceeded max allowed {self.max_null_rate:.2%}."
                if not passed
                else f"Column '{self.column}' null rate {actual_null_rate:.2%} is within allowed threshold {self.max_null_rate:.2%}."
            )

        samples: list[Any] = [None] if null_count > 0 else []
        return passed, total_rows, null_count, samples, msg
