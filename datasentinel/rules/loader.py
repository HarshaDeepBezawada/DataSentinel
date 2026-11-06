"""YAML rule loader with Pydantic v2 configuration validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from datasentinel.core.exceptions import ConfigurationError, RuleValidationError
from datasentinel.rules.models import PipelineConfig, RuleConfig


class RuleLoader:
    """Loads and validates pipeline configuration and rules from YAML files."""

    @classmethod
    def load_yaml(cls, path_or_stream: str | Path) -> dict[str, Any]:
        """Read YAML file safely."""
        path = Path(path_or_stream)
        if not path.is_file():
            raise ConfigurationError(
                f"Configuration file not found: '{path_or_stream}'",
                details=f"Current working directory: {os.getcwd()}",
            )
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ConfigurationError(f"YAML content in '{path}' must be a key-value dictionary.")
                return data
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML syntax error in '{path}': {e}") from e

    @classmethod
    def load_pipeline(cls, path_or_stream: str | Path) -> PipelineConfig:
        """Parse and validate entire pipeline configuration via Pydantic v2."""
        raw_dict = cls.load_yaml(path_or_stream)
        try:
            return PipelineConfig.model_validate(raw_dict)
        except ValidationError as e:
            err_messages = []
            for err in e.errors():
                loc = " -> ".join(str(p) for p in err["loc"])
                err_messages.append(f"Field '{loc}': {err['msg']}")
            raise RuleValidationError(
                f"Invalid pipeline configuration in '{path_or_stream}':\n" + "\n".join(err_messages)
            ) from e

    @classmethod
    def load_rules(cls, path_or_stream: str | Path) -> list[RuleConfig]:
        """Convenience helper to extract rule configs from pipeline."""
        pipeline = cls.load_pipeline(path_or_stream)
        return pipeline.rules
