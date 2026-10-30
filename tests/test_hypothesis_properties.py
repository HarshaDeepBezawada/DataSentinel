"""Property-based tests using Hypothesis for validation logic and anomaly detection."""

import math
from hypothesis import given, settings, strategies as st
import pandas as pd

from datasentinel.anomaly.iqr import IQRAnomalyDetector
from datasentinel.anomaly.zscore import ZScoreAnomalyDetector
from datasentinel.core.dataset import DataSet
from datasentinel.rules.null_check import NullCheckRule
from datasentinel.rules.range_check import RangeCheckRule


@given(st.lists(st.floats(min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False), min_size=20, max_size=200))
@settings(max_examples=30)
def test_hypothesis_injected_extreme_outlier_detected(numbers: list[float]) -> None:
    """Property: An extreme outlier (orders of magnitude beyond spread) is always detected by Z-score."""
    # Ensure some standard deviation
    numbers[0] = 0.0
    numbers[1] = 10.0
    # Inject extreme outlier
    extreme_val = 1e9
    test_data = numbers + [extreme_val]

    df = pd.DataFrame({"col": test_data})
    ds = DataSet("hyp_outlier", data=df)

    detector = ZScoreAnomalyDetector(threshold=3.0)
    summary = detector.detect(ds, "col")

    assert summary.total_anomalies >= 1
    found_values = [p.value for p in summary.sample_anomalies]
    assert any(math.isclose(v, extreme_val, rel_tol=1e-3) for v in found_values)


@given(st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False), st.integers(min_value=10, max_value=100))
@settings(max_examples=25)
def test_hypothesis_constant_values_no_anomalies(val: float, count: int) -> None:
    """Property: A column with identical constant values has 0 standard deviation and 0 anomalies."""
    df = pd.DataFrame({"col": [val] * count})
    ds = DataSet("hyp_constant", data=df)

    z_summary = ZScoreAnomalyDetector().detect(ds, "col")
    assert z_summary.total_anomalies == 0

    iqr_summary = IQRAnomalyDetector().detect(ds, "col")
    assert iqr_summary.total_anomalies == 0


@given(
    st.floats(min_value=-100.0, max_value=0.0, allow_nan=False),
    st.floats(min_value=1.0, max_value=100.0, allow_nan=False),
)
@settings(max_examples=30)
def test_hypothesis_range_rule_invariant(min_val: float, max_val: float) -> None:
    """Property: Any values generated inside [min_val, max_val] must strictly pass the RangeCheckRule."""
    step = (max_val - min_val) / 10.0
    valid_numbers = [min_val + i * step * 0.999 for i in range(10)] + [min_val, max_val]

    df = pd.DataFrame({"val": valid_numbers})
    ds = DataSet("hyp_range", data=df)

    rule = RangeCheckRule(rule_id="H_R1", column="val", min_value=min_val, max_value=max_val, inclusive=True)
    res = rule.evaluate(ds)
    assert res.passed is True
    assert res.failed_rows == 0


@given(st.lists(st.integers(min_value=1, max_value=10000), min_size=5, max_size=50))
@settings(max_examples=25)
def test_hypothesis_null_check_invariant(integers: list[int]) -> None:
    """Property: A list of purely non-null integers must always pass NullCheckRule."""
    df = pd.DataFrame({"int_col": integers})
    ds = DataSet("hyp_null", data=df)

    rule = NullCheckRule(rule_id="H_N1", column="int_col", allow_nulls=False)
    res = rule.evaluate(ds)
    assert res.passed is True
    assert res.failed_rows == 0
