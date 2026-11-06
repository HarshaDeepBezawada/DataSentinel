"""Rule executor applying configured quality checks across datasets."""

from __future__ import annotations

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import RuleResult
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import PipelineConfig
from datasentinel.rules.registry import RuleRegistry


class RuleExecutor:
    """Executes a suite of validation rules against a DataSet."""

    def __init__(self, rules: list[BaseRule]) -> None:
        self.rules = rules

    @classmethod
    def from_pipeline_config(cls, config: PipelineConfig) -> RuleExecutor:
        """Construct executor directly from a validated PipelineConfig."""
        rules: list[BaseRule] = []
        for rule_cfg in config.rules:
            rule_instance = RuleRegistry.create_from_config(rule_cfg)
            rules.append(rule_instance)
        return cls(rules)

    def execute(self, dataset: DataSet, show_progress: bool = False) -> list[RuleResult]:
        """Execute all rules, optionally showing a Rich progress bar."""
        results: list[RuleResult] = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Applying quality rules...", total=len(self.rules))
                for rule in self.rules:
                    progress.update(task, description=f"[cyan]Evaluating rule '{rule.rule_id}' ({rule.column})...")
                    res = rule.evaluate(dataset)
                    results.append(res)
                    progress.advance(task)
        else:
            for rule in self.rules:
                res = rule.evaluate(dataset)
                results.append(res)

        return results
