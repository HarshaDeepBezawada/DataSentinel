"""Tests for Typer CLI commands."""

import re
from pathlib import Path

from typer.testing import CliRunner

from datasentinel.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    """Test CLI root help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "DataSentinel" in result.stdout
    assert "validate" in result.stdout
    assert "report" in result.stdout
    assert "compare-schemas" in result.stdout
    assert "schedule" in result.stdout
    assert "list-rules" in result.stdout


def test_cli_list_rules() -> None:
    """Test list-rules command against sample YAML configs."""
    result = runner.invoke(app, ["list-rules", "config/ecommerce_orders.yaml"])
    assert result.exit_code == 0
    assert "E-Commerce Orders Validation" in result.stdout
    assert "Total configured rules: 6" in result.stdout


def test_cli_validate() -> None:
    """Test validate command on ecommerce_orders.yaml (returns exit code 0 on 100% clean data)."""
    result = runner.invoke(app, ["validate", "config/ecommerce_orders.yaml", "--quiet"])
    assert result.exit_code == 0
    assert "E-Commerce Orders Validation" in result.stdout


def test_cli_validate_failures() -> None:
    """Test validate command on ecommerce_orders_failures.yaml (returns exit code 1 due to violations)."""
    result = runner.invoke(app, ["validate", "config/ecommerce_orders_failures.yaml", "--quiet"])
    assert result.exit_code == 1
    assert "E-Commerce Orders Validation" in result.stdout


def test_cli_report(tmp_path: Path) -> None:
    """Test report generation command."""
    html_out = tmp_path / "cli_report.html"
    pdf_out = tmp_path / "cli_report.pdf"

    result = runner.invoke(app, [
        "report",
        "config/ecommerce_orders.yaml",
        "--html", str(html_out),
        "--pdf", str(pdf_out),
    ])
    assert result.exit_code == 0
    assert html_out.exists()
    assert pdf_out.exists()


def test_cli_compare_schemas() -> None:
    """Test compare-schemas command."""
    result = runner.invoke(app, [
        "compare-schemas",
        "data/ecommerce_orders_drifted.csv",
        "--baseline", "data/ecommerce_orders.csv",
    ])
    assert result.exit_code == 0
    assert "REMOVED" in result.stdout
    assert "ADDED" in result.stdout


def test_cli_validate_json_flags(tmp_path: Path) -> None:
    """Test --export-json and --json flags for pipeline orchestration integration."""
    json_export = tmp_path / "metrics.json"
    result = runner.invoke(app, [
        "validate",
        "config/inventory_json.yaml",
        "--export-json", str(json_export),
    ])
    assert result.exit_code == 0
    assert json_export.exists()
    assert "Exported machine-readable JSON metrics" in result.stdout

    # Test stdout json output
    res_stdout = runner.invoke(app, [
        "validate",
        "config/inventory_json.yaml",
        "--json",
    ])
    assert res_stdout.exit_code == 0
    assert '"pipeline_name": "Inventory Products JSON Pipeline"' in res_stdout.stdout


def test_cli_schedule_help() -> None:
    """Test CLI schedule command help text and options."""
    result = runner.invoke(app, ["schedule", "--help"])
    assert result.exit_code == 0
    clean_stdout = re.sub(r"\x1b\[[0-9;]*[mK]", "", result.stdout)
    assert "--cron" in clean_stdout
    assert "APScheduler" in clean_stdout


def test_cli_exit_code_on_missing_config() -> None:
    """Verify that nonexistent config returns exit code 2."""
    result = runner.invoke(app, ["validate", "config/nonexistent_config_file.yaml"])
    assert result.exit_code == 2
