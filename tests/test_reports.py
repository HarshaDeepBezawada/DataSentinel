"""Tests for HTML and PDF report generators."""

from pathlib import Path
import pytest

from datasentinel.core.types import (
    AnomalyPoint,
    AnomalySummary,
    DriftItem,
    DriftReport,
    DriftType,
    PipelineRunResult,
    RuleResult,
    ValidationStatus,
)
from datasentinel.reports.html_generator import HTMLReportGenerator
from datasentinel.reports.pdf_generator import PDFReportGenerator


@pytest.fixture
def mock_run_result() -> PipelineRunResult:
    """Fixture providing a complete mock PipelineRunResult."""
    return PipelineRunResult(
        run_id="run-test-1234",
        pipeline_name="Automated Test Pipeline",
        timestamp="2026-10-30 10:00:00 UTC",
        duration_ms=125.4,
        total_rows=1500,
        total_columns=5,
        rules_passed=4,
        rules_failed=1,
        rules_warning=0,
        rule_results=[
            RuleResult(
                rule_id="R1",
                rule_type="null_check",
                column="id",
                status=ValidationStatus.PASSED,
                passed=True,
                total_rows=1500,
                failed_rows=0,
                failure_rate=0.0,
                message="Zero nulls found.",
            ),
            RuleResult(
                rule_id="R2",
                rule_type="range",
                column="amount",
                status=ValidationStatus.FAILED,
                passed=False,
                total_rows=1500,
                failed_rows=12,
                failure_rate=0.008,
                sample_failures=[-5.0, 99999.0],
                message="Found 12 values out of range.",
            ),
        ],
        drift_report=DriftReport(
            baseline_name="baseline_test",
            current_name="current_test",
            has_drift=True,
            diffs=[
                DriftItem(
                    drift_type=DriftType.ADDED,
                    column_name="new_col",
                    baseline_value=None,
                    current_value="int64",
                    message="New column added.",
                )
            ],
            summary="1 difference detected.",
        ),
        anomalies=[
            AnomalySummary(
                column="amount",
                method="zscore",
                total_anomalies=2,
                anomaly_rate=0.0013,
                sample_anomalies=[
                    AnomalyPoint(
                        column="amount",
                        row_index=42,
                        value=99999.0,
                        score=0.95,
                        method="zscore",
                        message="Z-score > 3.0",
                    )
                ],
                mean=120.0,
                std=15.0,
            )
        ],
        overall_status=ValidationStatus.FAILED,
    )


def test_html_report_generator(mock_run_result: PipelineRunResult, tmp_path: Path) -> None:
    """Test generating Jinja2 HTML report with Chart.js."""
    generator = HTMLReportGenerator()
    out_file = tmp_path / "report.html"

    result_path = generator.generate(mock_run_result, out_file)
    assert result_path.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "<title>DataSentinel Quality Report" in content
    assert "Automated Test Pipeline" in content
    assert "chart.js" in content
    assert "run-test-1234" in content
    assert "new_col" in content


def test_pdf_report_generator(mock_run_result: PipelineRunResult, tmp_path: Path) -> None:
    """Test generating ReportLab PDF report."""
    generator = PDFReportGenerator()
    out_file = tmp_path / "report.pdf"

    result_path = generator.generate(mock_run_result, out_file)
    assert result_path.exists()
    assert out_file.stat().st_size > 1000

    # Verify standard PDF header magic bytes
    with open(out_file, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"
