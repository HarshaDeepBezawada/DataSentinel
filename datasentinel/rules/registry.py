"""Rule registry for discovering and instantiating validation rules."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from datasentinel.core.exceptions import RuleValidationError
from datasentinel.rules.base import BaseRule
from datasentinel.rules.models import RuleConfig


class RuleRegistry:
    """Registry for data quality rules."""

    _rules: ClassVar[dict[str, type[BaseRule]]] = {}

    @classmethod
    def register(cls, rule_type: str) -> Callable[[type[BaseRule]], type[BaseRule]]:
        """Decorator to register a rule class."""
        def decorator(rule_cls: type[BaseRule]) -> type[BaseRule]:
            cls._rules[rule_type.lower()] = rule_cls
            return rule_cls
        return decorator

    @classmethod
    def get(cls, rule_type: str) -> type[BaseRule]:
        rule_key = rule_type.lower()
        if rule_key not in cls._rules:
            available = ", ".join(sorted(cls._rules.keys()))
            raise RuleValidationError(
                f"Unknown rule type: '{rule_type}'. Available rules: [{available}]"
            )
        return cls._rules[rule_key]

    @classmethod
    def create_from_config(cls, config: RuleConfig) -> BaseRule:
        rule_cls = cls.get(config.type)
        # Type-specific instantiation handled by classes
        return rule_cls.from_config(config)  # type: ignore[attr-defined, no-any-return]

    @classmethod
    def list_available(cls) -> list[str]:
        return sorted(cls._rules.keys())
