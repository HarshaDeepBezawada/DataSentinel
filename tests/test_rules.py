"""Tests for rule implementations, YAML loader, and executor."""

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from datasentinel.core.dataset import DataSet
from datasentinel.core.exceptions import ConfigurationError, RuleValidationError
from datasentinel.core.types import ValidationStatus
from datasentinel.rules.executor import RuleExecutor
from datasentinel.rules.foreign_key_check import ForeignKeyRule
from datasentinel.rules.loader import RuleLoader
from datasentinel.rules.models import RegexCheckConfig
from datasentinel.rules.null_check import NullCheckRule
from datasentinel.rules.range_check import RangeCheckRule
from datasentinel.rules.regex_check import RegexCheckRule
from datasentinel.rules.unique_check import UniqueCheckRule


def test_null_check_rule() -> None:
    """Test null check with strict zero tolerance and allowed rate."""
    df = pd.DataFrame({"col": [1, None, 3, 4, None]})
    ds = DataSet("test_null", data=df)

    rule_strict = NullCheckRule(rule_id="R1", column="col", allow_nulls=False)
    res = rule_strict.evaluate(ds)
    assert res.passed is False
    assert res.failed_rows == 2
    assert res.status == ValidationStatus.FAILED

    rule_lenient = NullCheckRule(rule_id="R2", column="col", allow_nulls=True, max_null_rate=0.5)
    res_lenient = rule_lenient.evaluate(ds)
    assert res_lenient.passed is True

    # Missing column
    res_missing = NullCheckRule(rule_id="R3", column="absent_col").evaluate(ds)
    assert res_missing.status == ValidationStatus.ERROR


def test_unique_check_rule() -> None:
    """Test uniqueness validation and duplicate reporting."""
    df = pd.DataFrame({"id": ["A", "B", "A", "C", "D"]})
    ds = DataSet("test_unique", data=df)

    rule = UniqueCheckRule(rule_id="U1", column="id", min_unique_rate=1.0)
    res = rule.evaluate(ds)
    assert res.passed is False
    assert "A" in res.sample_failures

    rule_tolerant = UniqueCheckRule(rule_id="U2", column="id", min_unique_rate=0.7)
    res_tolerant = rule_tolerant.evaluate(ds)
    assert res_tolerant.passed is True


def test_range_check_rule() -> None:
    """Test numeric range boundaries and inclusivity."""
    df = pd.DataFrame({"val": [10.0, 15.0, 20.0, 25.0, 5.0, 50.0]})
    ds = DataSet("test_range", data=df)

    rule_inclusive = RangeCheckRule(rule_id="RG1", column="val", min_value=10.0, max_value=25.0, inclusive=True)
    res = rule_inclusive.evaluate(ds)
    assert res.passed is False
    assert res.failed_rows == 2  # 5.0 and 50.0

    rule_exclusive = RangeCheckRule(rule_id="RG2", column="val", min_value=10.0, max_value=25.0, inclusive=False)
    res_ex = rule_exclusive.evaluate(ds)
    assert res_ex.failed_rows == 4  # 10.0, 25.0, 5.0, 50.0


def test_regex_check_rule() -> None:
    """Test string regex matching."""
    df = pd.DataFrame({"email": ["valid@test.com", "also.valid@domain.org", "invalid-email"]})
    ds = DataSet("test_regex", data=df)

    rule = RegexCheckRule(rule_id="RX1", column="email", pattern=r"^[\w\.]+@\w+\.\w+$")
    res = rule.evaluate(ds)
    assert res.passed is False
    assert res.failed_rows == 1
    assert "invalid-email" in res.sample_failures


def test_email_regex_rfc_validation() -> None:
    """Test standard RFC email regex validation with valid, malformed, and null values."""
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    # Valid emails
    df_valid = pd.DataFrame({
        "email": [
            "user@example.com",
            "first.last+tag@sub.domain.co",
            "developer_123@company-name.io",
        ]
    })
    res_valid = RegexCheckRule("RX_VAL", "email", email_pattern).evaluate(DataSet("ds_valid", data=df_valid))
    assert res_valid.passed is True
    assert res_valid.failed_rows == 0

    # Malformed emails
    df_invalid = pd.DataFrame({
        "email": [
            "plainaddress",
            "missingatsign.com",
            "user@domain@domain.com",
            "user@.com",
            "hannah@not-an-email",
        ]
    })
    res_invalid = RegexCheckRule("RX_INVAL", "email", email_pattern).evaluate(DataSet("ds_invalid", data=df_invalid))
    assert res_invalid.passed is False
    assert res_invalid.failed_rows == 5
    assert len(res_invalid.sample_failures) == 5

    # Null values: Nulls are ignored by regex rule (to be caught by null_check rule)
    df_nulls = pd.DataFrame({"email": ["valid@test.com", None, "another.valid@test.com", None]})
    res_nulls = RegexCheckRule("RX_NULL", "email", email_pattern).evaluate(DataSet("ds_nulls", data=df_nulls))
    assert res_nulls.passed is True
    assert res_nulls.failed_rows == 0


def test_regex_config_validation() -> None:
    """Verify that invalid regex patterns raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        RegexCheckConfig(pattern="[unclosed-class")


def test_foreign_key_rule() -> None:
    """Test foreign key / referential integrity check."""
    df = pd.DataFrame({
        "status": ["active", "pending", "banned", "active"],
        "category_id": [1, 2, 999, 1],
        "allowed_category": [1, 2, 3, 4],
    })
    ds = DataSet("test_fk", data=df)

    # In explicit value list
    rule_values = ForeignKeyRule(
        rule_id="FK1",
        column="status",
        reference_values=["active", "pending", "closed"],
    )
    res = rule_values.evaluate(ds)
    assert res.passed is False
    assert "banned" in res.sample_failures

    # Cross-column check
    rule_cross = ForeignKeyRule(
        rule_id="FK2",
        column="category_id",
        reference_column="allowed_category",
    )
    res_cross = rule_cross.evaluate(ds)
    assert res_cross.passed is False
    assert 999 in res_cross.sample_failures


def test_rule_loader_validation(tmp_path: Path) -> None:
    """Test RuleLoader with valid and invalid YAML configs."""
    valid_yaml = tmp_path / "valid.yaml"
    valid_yaml.write_text(
        """
name: "Test Pipeline"
source:
  type: "csv"
  name: "source1"
  options:
    path: "data.csv"
rules:
  - id: "R1"
    type: "null_check"
    column: "id"
    severity: "error"
    params:
      allow_nulls: false
"""
    )
    cfg = RuleLoader.load_pipeline(valid_yaml)
    assert cfg.name == "Test Pipeline"
    assert len(cfg.rules) == 1

    # Invalid YAML (syntax error)
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("name: [unclosed list\n")
    with pytest.raises(ConfigurationError):
        RuleLoader.load_pipeline(bad_yaml)

    # Invalid model (missing required fields)
    invalid_schema = tmp_path / "invalid_schema.yaml"
    invalid_schema.write_text("name: Test\n")
    with pytest.raises(RuleValidationError):
        RuleLoader.load_pipeline(invalid_schema)


def test_rule_executor(sample_orders_dataset: DataSet) -> None:
    """Test RuleExecutor executing multiple rules against sample dataset."""
    rules = [
        NullCheckRule(rule_id="R1", column="order_id", allow_nulls=False),
        UniqueCheckRule(rule_id="R2", column="order_id", min_unique_rate=1.0),
        RangeCheckRule(rule_id="R3", column="total_amount", min_value=0.0, max_value=500.0),
    ]
    executor = RuleExecutor(rules)
    results = executor.execute(sample_orders_dataset, show_progress=False)

    assert len(results) == 3
    # order_id has 0 nulls -> R1 passed
    assert results[0].passed is True
    # order_id has duplicate 'ORD-1' -> R2 failed
    assert results[1].passed is False
    # total_amount has negative -10 and extreme 99999 -> R3 failed
    assert results[2].passed is False
