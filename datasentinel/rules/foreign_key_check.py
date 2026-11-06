"""Referential integrity / foreign key validation rule."""

from __future__ import annotations

from typing import Any

import pandas as pd

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import Severity
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import ForeignKeyConfig, RuleConfig
from datasentinel.rules.registry import RuleRegistry


@RuleRegistry.register("foreign_key")
@RuleRegistry.register("referential_integrity")
@RuleRegistry.register("in_set")
class ForeignKeyRule(BaseRule):
    """Rule verifying that column values reference a valid set of keys (cross-column, list, or external source)."""

    def __init__(
        self,
        rule_id: str,
        column: str,
        reference_column: str | None = None,
        reference_values: list[Any] | None = None,
        reference_dataset: str | None = None,
        description: str | None = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        super().__init__(
            rule_id=rule_id,
            rule_type="foreign_key",
            column=column,
            description=description,
            severity=severity,
        )
        self.reference_column = reference_column
        self.reference_values = set(reference_values) if reference_values is not None else None
        self.reference_dataset = reference_dataset

    @classmethod
    def from_config(cls, config: RuleConfig) -> ForeignKeyRule:
        params = ForeignKeyConfig(**config.params)
        return cls(
            rule_id=config.id,
            column=config.column,
            reference_column=params.reference_column,
            reference_values=params.reference_values,
            reference_dataset=params.reference_dataset,
            description=config.description,
            severity=config.severity,
        )

    def _load_reference_keys(self, dataset: DataSet) -> set[Any]:
        """Resolve valid keys from reference values, cross-column, or external file."""
        if self.reference_values is not None:
            return set(self.reference_values)

        if self.reference_column is not None:
            df = dataset.to_dataframe()
            if self.reference_column in df.columns:
                return set(df[self.reference_column].dropna().unique())
            raise ValueError(f"Cross-reference column '{self.reference_column}' not found in dataset.")

        if self.reference_dataset is not None:
            ref_df = pd.read_csv(self.reference_dataset)
            ref_col = self.reference_column or ref_df.columns[0]
            return set(ref_df[ref_col].dropna().unique())

        return set()

    def run_check(self, dataset: DataSet) -> tuple[bool, int, int, list[Any], str]:
        valid_keys = self._load_reference_keys(dataset)

        total_rows = 0
        failed_count = 0
        samples: list[Any] = []

        for chunk in dataset.iter_chunks():
            total_rows += len(chunk)
            series = chunk[self.column].dropna()
            # Check membership
            invalid_mask = ~series.isin(valid_keys)
            violators = series[invalid_mask]
            failed_count += len(violators)
            if len(samples) < 5 and len(violators) > 0:
                samples.extend(violators.head(5 - len(samples)).tolist())

        if total_rows == 0:
            return True, 0, 0, [], "Dataset is empty."

        passed = failed_count == 0

        target_desc = (
            f"column '{self.reference_column}'"
            if self.reference_column
            else f"set of {len(valid_keys)} reference values"
        )

        if passed:
            msg = f"All values in '{self.column}' exist in {target_desc}."
        else:
            msg = (
                f"Column '{self.column}' has {failed_count} orphaned/invalid foreign keys not found in {target_desc}. "
                f"Sample invalid keys: {samples}."
            )

        return passed, total_rows, failed_count, samples, msg
