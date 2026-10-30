"""Tests for schema fingerprinting, registry, and drift detection."""

from pathlib import Path
import pandas as pd
import pytest

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import DriftType
from datasentinel.schema.diff import SchemaDriftDetector
from datasentinel.schema.fingerprint import SchemaFingerprintGenerator
from datasentinel.schema.registry import SchemaRegistry


def test_schema_fingerprint_generation() -> None:
    """Test schema fingerprint extraction from dataset."""
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", None],
        "score": [95.5, 80.0, 75.2],
    })
    ds = DataSet("test_fp", data=df)
    fp = SchemaFingerprintGenerator.generate(ds)

    assert fp.dataset_name == "test_fp"
    assert fp.column_count == 3
    assert fp.row_count == 3
    assert fp.columns["id"].nullable is False
    assert fp.columns["name"].nullable is True
    assert fp.columns["score"].dtype == "float64"


def test_schema_registry_save_load(tmp_path: Path) -> None:
    """Test persisting and reading baselines in SchemaRegistry."""
    reg = SchemaRegistry(storage_dir=tmp_path)
    df = pd.DataFrame({"col1": [10, 20]})
    ds = DataSet("pipeline_a", data=df)
    fp = ds.fingerprint()

    saved_path = reg.save_baseline("pipeline_a", fp)
    assert saved_path.exists()

    loaded = reg.load_baseline("pipeline_a")
    assert loaded is not None
    assert loaded.dataset_name == "pipeline_a"
    assert "col1" in loaded.columns

    # Non-existent baseline
    assert reg.load_baseline("missing_pipeline") is None


def test_schema_drift_detector() -> None:
    """Test comprehensive drift detection diffs."""
    base_df = pd.DataFrame({
        "id": [1, 2, 3],
        "email": ["a@x.com", "b@x.com", "c@x.com"],  # strictly not-null
        "age": [25, 30, 35],                          # int64
        "legacy_col": ["old1", "old2", "old3"],
    })
    base_fp = DataSet("baseline", data=base_df).fingerprint()

    curr_df = pd.DataFrame({
        "id": [1, 2, 3],
        "email": ["a@x.com", None, "c@x.com"],       # nullability changed!
        "age": [25.5, 30.0, 35.2],                   # type changed: int64 -> float64!
        "new_feature": [True, False, True],          # added!
        # legacy_col removed!
    })
    curr_fp = DataSet("current", data=curr_df).fingerprint()

    report = SchemaDriftDetector.compare(base_fp, curr_fp)
    assert report.has_drift is True
    assert len(report.diffs) == 4

    drift_types = {d.drift_type for d in report.diffs}
    assert DriftType.REMOVED in drift_types
    assert DriftType.ADDED in drift_types
    assert DriftType.TYPE_CHANGED in drift_types
    assert DriftType.NULLABILITY_CHANGED in drift_types

    # Test identical schemas
    identical_report = SchemaDriftDetector.compare(base_fp, base_fp)
    assert identical_report.has_drift is False
    assert len(identical_report.diffs) == 0
