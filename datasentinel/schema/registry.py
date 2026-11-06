"""Schema registry storing and retrieving baseline fingerprints."""

from __future__ import annotations

from pathlib import Path

from datasentinel.core.exceptions import SchemaDriftError
from datasentinel.core.types import SchemaFingerprint


class SchemaRegistry:
    """Manages persistent baseline fingerprints for pipeline schema monitoring."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or Path(".datasentinel/schemas")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, pipeline_name: str, custom_path: Path | None = None) -> Path:
        if custom_path:
            return custom_path
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in pipeline_name)
        return self.storage_dir / f"{safe_name}_baseline.json"

    def save_baseline(
        self,
        pipeline_name: str,
        fingerprint: SchemaFingerprint,
        custom_path: Path | None = None,
    ) -> Path:
        """Persist a baseline schema fingerprint to disk."""
        target_path = self._get_path(pipeline_name, custom_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(fingerprint.model_dump_json(indent=2))
            return target_path
        except Exception as e:
            raise SchemaDriftError(f"Failed to save baseline schema to '{target_path}': {e}") from e

    def load_baseline(
        self,
        pipeline_name: str,
        custom_path: Path | None = None,
    ) -> SchemaFingerprint | None:
        """Load a persisted baseline schema fingerprint, or None if not found."""
        target_path = self._get_path(pipeline_name, custom_path)
        if not target_path.is_file():
            return None
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = f.read()
            return SchemaFingerprint.model_validate_json(content)
        except Exception as e:
            raise SchemaDriftError(f"Failed to load baseline schema from '{target_path}': {e}") from e

    def list_baselines(self) -> list[str]:
        """Return names of all stored baselines."""
        return [p.stem.replace("_baseline", "") for p in self.storage_dir.glob("*_baseline.json")]
