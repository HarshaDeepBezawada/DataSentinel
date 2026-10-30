"""Regex pattern matching validation rule."""

from __future__ import annotations

import re
from typing import Any, List, Optional
import pandas as pd

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import Severity
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import RegexCheckConfig, RuleConfig
from datasentinel.rules.registry import RuleRegistry


@RuleRegistry.register("regex")
@RuleRegistry.register("regex_check")
@RuleRegistry.register("pattern")
class RegexCheckRule(BaseRule):
    """Rule verifying that string column values match a specified regular expression."""

    def __init__(
        self,
        rule_id: str,
        column: str,
        pattern: str,
        full_match: bool = True,
        description: Optional[str] = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            rule_type="regex",
            column=column,
            description=description,
            severity=severity,
        )
        self.pattern = pattern
        self.full_match = full_match
        self._compiled_regex = re.compile(pattern)

    @classmethod
    def from_config(cls, config: RuleConfig) -> RegexCheckRule:
        params = RegexCheckConfig(**config.params)
        return cls(
            rule_id=config.id,
            column=config.column,
            pattern=params.pattern,
            full_match=params.full_match,
            description=config.description,
            severity=config.severity,
        )

    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, List[Any], str]:
        total_rows = 0
        failed_count = 0
        samples: List[Any] = []

        for chunk in dataset.iter_chunks():
            total_rows += len(chunk)
            series = chunk[self.column].dropna().astype(str)

            if self.full_match:
                matches = series.str.match(self.pattern, na=False)
            else:
                matches = series.str.contains(self.pattern, na=False)

            violators = series[~matches]
            failed_count += len(violators)
            if len(samples) < 5 and len(violators) > 0:
                samples.extend(violators.head(5 - len(samples)).tolist())

        if total_rows == 0:
            return True, 0, 0, [], "Dataset is empty."

        passed = failed_count == 0

        if passed:
            msg = f"All non-null values in '{self.column}' match pattern '{self.pattern}'."
        else:
            msg = (
                f"Column '{self.column}' has {failed_count} values that do not match pattern '{self.pattern}'. "
                f"Sample violations: {samples}."
            )

        return passed, total_rows, failed_count, samples, msg
