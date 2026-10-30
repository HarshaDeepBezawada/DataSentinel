"""DataSentinel CLI - Automated Data Quality & Pipeline Monitoring Platform."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Optional
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from datasentinel.alerts.manager import AlertManager
from datasentinel.anomaly.detector import StatisticalAnomalyDetector
from datasentinel.connectors.registry import ConnectorRegistry
from datasentinel.core.exceptions import DataSentinelError
from datasentinel.core.types import PipelineRunResult, ValidationStatus
from datasentinel.reports.html_generator import HTMLReportGenerator
from datasentinel.reports.pdf_generator import PDFReportGenerator
from datasentinel.rules.executor import RuleExecutor
from datasentinel.rules.loader import RuleLoader
from datasentinel.scheduler.runner import PipelineScheduler
from datasentinel.schema.diff import SchemaDriftDetector
from datasentinel.schema.registry import SchemaRegistry
from datasentinel.storage.history import RunHistoryStore

app = typer.Typer(
    name="datasentinel",
    help="DataSentinel - Enterprise Automated Data Quality & Pipeline Monitoring Platform.",
    add_completion=False,
)
console = Console()


def _run_pipeline(config_path: Path, show_progress: bool = True) -> PipelineRunResult:
    """Core orchestrator executing connector fetch, rules, schema diff, anomaly detection, and history."""
    start_time = time.perf_counter()
    pipeline_config = RuleLoader.load_pipeline(config_path)

    # 1. Fetch data through Connector Layer
    connector = ConnectorRegistry.create(
        source_type=pipeline_config.source.type,
        name=pipeline_config.source.name,
        options=pipeline_config.source.options,
    )
    dataset = connector.fetch_data()

    # 2. Schema Baseline & Drift Detection
    drift_report = None
    schema_reg = SchemaRegistry()
    current_fingerprint = dataset.fingerprint()

    if pipeline_config.schema_baseline:
        custom_base_path = Path(pipeline_config.schema_baseline.fingerprint_path) if pipeline_config.schema_baseline.fingerprint_path else None
        baseline = schema_reg.load_baseline(pipeline_config.name, custom_base_path)
        if baseline is not None:
            drift_report = SchemaDriftDetector.compare(baseline, current_fingerprint)
        else:
            # Register current as initial baseline if none exists
            schema_reg.save_baseline(pipeline_config.name, current_fingerprint, custom_base_path)

        if pipeline_config.schema_baseline.auto_update:
            schema_reg.save_baseline(pipeline_config.name, current_fingerprint, custom_base_path)

    # 3. Rule Execution
    executor = RuleExecutor.from_pipeline_config(pipeline_config)
    rule_results = executor.execute(dataset, show_progress=show_progress)

    # 4. Statistical Anomaly Detection
    anomalies = []
    if pipeline_config.anomaly_detection and pipeline_config.anomaly_detection.enabled:
        detector = StatisticalAnomalyDetector(pipeline_config.anomaly_detection)
        anomalies = detector.detect_all(dataset, show_progress=show_progress)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    # Calculate summary counts
    passed_count = sum(1 for r in rule_results if r.passed)
    failed_count = sum(1 for r in rule_results if not r.passed and r.status == ValidationStatus.FAILED)
    warn_count = sum(1 for r in rule_results if not r.passed and r.status == ValidationStatus.WARNING)

    overall_status = ValidationStatus.PASSED
    if failed_count > 0:
        overall_status = ValidationStatus.FAILED
    elif warn_count > 0 or (drift_report and drift_report.has_drift):
        overall_status = ValidationStatus.WARNING

    total_rows = dataset.shape[0] if dataset.shape[0] > 0 else (len(dataset.to_dataframe()))
    total_cols = len(dataset.columns)

    run_result = PipelineRunResult(
        run_id=f"run-{uuid.uuid4().hex[:8]}",
        pipeline_name=pipeline_config.name,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        duration_ms=round(elapsed_ms, 2),
        total_rows=total_rows,
        total_columns=total_cols,
        rules_passed=passed_count,
        rules_failed=failed_count,
        rules_warning=warn_count,
        rule_results=rule_results,
        drift_report=drift_report,
        anomalies=anomalies,
        overall_status=overall_status,
    )

    # Record in history store
    history_store = RunHistoryStore()
    history_store.record_run(run_result)

    # Dispatch alerts if configured
    if pipeline_config.alerts:
        alert_mgr = AlertManager(pipeline_config.alerts)
        alert_mgr.dispatch(run_result)

    return run_result


@app.command("validate")
def validate_command(
    config: Path = typer.Argument(
        ...,
        help="Path to YAML rule configuration file. Example: config/ecommerce_orders.yaml",
        exists=True,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress progress bars and verbose messages.",
    ),
) -> None:
    """Validate data sources against YAML quality rules and detect anomalies.

    \b
    Examples:
      datasentinel validate config/ecommerce_orders.yaml
      datasentinel validate config/hr_data.yaml --quiet
    """
    try:
        if not quiet:
            console.print(
                Panel.fit(
                    f"[bold blue]DataSentinel Validator[/bold blue]\n[dim]Loading config: {config}[/dim]",
                    border_style="blue",
                )
            )

        result = _run_pipeline(config, show_progress=not quiet)

        # Output Summary Table
        summary_table = Table(title=f"Validation Run Summary: {result.pipeline_name}", border_style="cyan")
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value")

        summary_table.add_row("Run ID", result.run_id)
        summary_table.add_row("Execution Time", f"{result.duration_ms:.2f} ms")
        summary_table.add_row("Total Records", f"{result.total_rows:,}")
        summary_table.add_row("Total Columns", str(result.total_columns))
        summary_table.add_row("Passed Rules", f"[green]{result.rules_passed}[/green]")
        summary_table.add_row("Failed Rules", f"[red]{result.rules_failed}[/red]" if result.rules_failed > 0 else "0")
        summary_table.add_row("Warnings", f"[yellow]{result.rules_warning}[/yellow]" if result.rules_warning > 0 else "0")

        total_anomalies = sum(a.total_anomalies for a in result.anomalies)
        summary_table.add_row("Anomalies Found", f"[magenta]{total_anomalies}[/magenta]")

        if result.drift_report:
            drift_str = (
                f"[yellow]DRIFT DETECTED ({len(result.drift_report.diffs)} diffs)[/yellow]"
                if result.drift_report.has_drift
                else "[green]STABLE (in sync with baseline)[/green]"
            )
            summary_table.add_row("Schema Drift", drift_str)

        status_style = "green" if result.overall_status == ValidationStatus.PASSED else "red"
        summary_table.add_row("Overall Status", f"[{status_style}][bold]{result.overall_status.value.upper()}[/bold][/{status_style}]")

        console.print(summary_table)

        # Rules Detail Table
        rule_table = Table(title="Rule Evaluation Breakdown", border_style="dim")
        rule_table.add_column("Rule ID", style="bold")
        rule_table.add_column("Type")
        rule_table.add_column("Column")
        rule_table.add_column("Status")
        rule_table.add_column("Violations")
        rule_table.add_column("Details")

        for r in result.rule_results:
            status_badge = (
                "[green]PASS[/green]"
                if r.passed
                else ("[yellow]WARN[/yellow]" if r.status == ValidationStatus.WARNING else "[red]FAIL[/red]")
            )
            rule_table.add_row(
                r.rule_id,
                r.rule_type,
                r.column,
                status_badge,
                f"{r.failed_rows}/{r.total_rows} ({r.failure_rate * 100:.1f}%)",
                r.message,
            )
        console.print(rule_table)

        if result.overall_status == ValidationStatus.FAILED:
            raise typer.Exit(code=1)

    except DataSentinelError as e:
        console.print(f"[bold red]DataSentinel Error:[/bold red] {e}")
        raise typer.Exit(code=2)


@app.command("report")
def report_command(
    config: Path = typer.Argument(
        ...,
        help="Path to YAML rule configuration file.",
        exists=True,
    ),
    html: Optional[Path] = typer.Option(
        None,
        "--html",
        "-h",
        help="Target file path for executive HTML report.",
    ),
    pdf: Optional[Path] = typer.Option(
        None,
        "--pdf",
        "-p",
        help="Target file path for executive PDF report.",
    ),
) -> None:
    """Generate executive-quality HTML and PDF data quality reports with embedded charts.

    \b
    Examples:
      datasentinel report config/ecommerce_orders.yaml --html reports/orders_report.html
      datasentinel report config/ecommerce_orders.yaml --pdf reports/orders_report.pdf
      datasentinel report config/ecommerce_orders.yaml --html reports/out.html --pdf reports/out.pdf
    """
    try:
        console.print(f"[cyan]Executing pipeline for report generation...[/cyan]")
        result = _run_pipeline(config, show_progress=True)
        pipeline_cfg = RuleLoader.load_pipeline(config)
        history_store = RunHistoryStore()

        if not html and not pdf:
            # Default to html if neither specified
            html = Path(f"reports/{pipeline_cfg.name.lower().replace(' ', '_')}_report.html")

        if html:
            html_gen = HTMLReportGenerator()
            out_html = html_gen.generate(
                result=result,
                output_path=html,
                source_name=pipeline_cfg.source.name,
                history_store=history_store,
            )
            console.print(f"[bold green][OK] HTML Report generated successfully:[/bold green] {out_html}")

        if pdf:
            pdf_gen = PDFReportGenerator()
            out_pdf = pdf_gen.generate(
                result=result,
                output_path=pdf,
                source_name=pipeline_cfg.source.name,
            )
            console.print(f"[bold green][OK] PDF Report generated successfully:[/bold green] {out_pdf}")

    except DataSentinelError as e:
        console.print(f"[bold red]Error generating report:[/bold red] {e}")
        raise typer.Exit(code=2)


@app.command("compare-schemas")
def compare_schemas_command(
    source: Path = typer.Argument(
        ...,
        help="Target data source file (e.g. data.csv, data.json) or config YAML.",
        exists=True,
    ),
    baseline: Optional[Path] = typer.Option(
        None,
        "--baseline",
        "-b",
        help="Path to registered baseline fingerprint JSON, or baseline data file to compare against.",
    ),
) -> None:
    """Detect schema drift between datasets or against a stored baseline fingerprint.

    \b
    Examples:
      datasentinel compare-schemas data/current.csv --baseline data/baseline.csv
      datasentinel compare-schemas config/ecommerce_orders.yaml
    """
    try:
        schema_reg = SchemaRegistry()

        if source.suffix in (".yaml", ".yml"):
            cfg = RuleLoader.load_pipeline(source)
            conn = ConnectorRegistry.create(cfg.source.type, cfg.source.name, cfg.source.options)
            curr_ds = conn.fetch_data()
            curr_fp = curr_ds.fingerprint()
            base_fp = schema_reg.load_baseline(cfg.name, baseline)
            if base_fp is None:
                console.print(f"[yellow]No baseline found for '{cfg.name}'. Registering current schema as baseline.[/yellow]")
                saved = schema_reg.save_baseline(cfg.name, curr_fp, baseline)
                console.print(f"[green]Registered baseline at: {saved}[/green]")
                return
        else:
            # Compare two raw files
            source_type = source.suffix.lstrip(".")
            curr_conn = ConnectorRegistry.create(source_type, source.stem, {"path": str(source)})
            curr_ds = curr_conn.fetch_data()
            curr_fp = curr_ds.fingerprint()

            if baseline is None:
                console.print("[red]Error: --baseline must be specified when comparing raw data files.[/red]")
                raise typer.Exit(code=2)

            if baseline.suffix == ".json":
                try:
                    with open(baseline, "r", encoding="utf-8") as f:
                        base_fp = SchemaRegistry().load_baseline(baseline.stem, baseline)
                except Exception:
                    base_fp = None
            else:
                base_type = baseline.suffix.lstrip(".")
                base_conn = ConnectorRegistry.create(base_type, baseline.stem, {"path": str(baseline)})
                base_ds = base_conn.fetch_data()
                base_fp = base_ds.fingerprint()

        assert base_fp is not None
        report = SchemaDriftDetector.compare(base_fp, curr_fp)

        drift_table = Table(title=f"Schema Drift Analysis: {curr_fp.dataset_name}", border_style="yellow" if report.has_drift else "green")
        drift_table.add_column("Type", style="bold")
        drift_table.add_column("Column")
        drift_table.add_column("Baseline")
        drift_table.add_column("Current")
        drift_table.add_column("Details")

        if not report.diffs:
            console.print("[bold green][OK] No schema drift detected! Schemas are identical.[/bold green]")
            return

        for d in report.diffs:
            badge_color = "red" if d.drift_type == "removed" else ("cyan" if d.drift_type == "added" else "yellow")
            drift_table.add_row(
                f"[{badge_color}]{d.drift_type.upper()}[/{badge_color}]",
                d.column_name,
                d.baseline_value or "-",
                d.current_value or "-",
                d.message,
            )
        console.print(drift_table)

    except DataSentinelError as e:
        console.print(f"[bold red]Schema Drift Error:[/bold red] {e}")
        raise typer.Exit(code=2)


@app.command("schedule")
def schedule_command(
    config: Path = typer.Argument(
        ...,
        help="Path to YAML rule configuration file.",
        exists=True,
    ),
    cron: str = typer.Option(
        "*/10 * * * *",
        "--cron",
        "-c",
        help="Standard 5-field cron expression for recurring runs (e.g. '*/5 * * * *').",
    ),
) -> None:
    """Run recurring automated data quality validation with APScheduler and overlap prevention.

    \b
    Examples:
      datasentinel schedule config/ecommerce_orders.yaml --cron "0 * * * *"
      datasentinel schedule config/hr_data.yaml --cron "*/15 * * * *"
    """
    try:
        console.print(
            Panel.fit(
                f"[bold cyan]DataSentinel Automated Scheduler[/bold cyan]\n"
                f"Config: {config}\nCron Schedule: '{cron}'\n"
                f"Non-overlapping execution enabled (coalesce=True, max_instances=1).\n"
                f"Press Ctrl+C to stop.",
                border_style="cyan",
            )
        )

        def job() -> None:
            console.print(f"\n[dim][{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Triggering scheduled validation...[/dim]")
            _run_pipeline(config, show_progress=False)
            console.print(f"[green]Validation run completed and stored.[/green]")

        scheduler = PipelineScheduler()
        scheduler.schedule_cron(cron, job)
        scheduler.start()

    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped by user.[/yellow]")
    except DataSentinelError as e:
        console.print(f"[bold red]Scheduler Error:[/bold red] {e}")
        raise typer.Exit(code=2)


@app.command("list-rules")
def list_rules_command(
    config: Path = typer.Argument(
        ...,
        help="Path to YAML rule configuration file.",
        exists=True,
    ),
) -> None:
    """List all configured validation rules in a YAML file with their parameters.

    \b
    Examples:
      datasentinel list-rules config/ecommerce_orders.yaml
      datasentinel list-rules config/hr_data.yaml
    """
    try:
        pipeline = RuleLoader.load_pipeline(config)

        table = Table(title=f"Configured Quality Rules: {pipeline.name}", border_style="blue")
        table.add_column("Rule ID", style="bold cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Column", style="yellow")
        table.add_column("Severity")
        table.add_column("Parameters", style="dim")
        table.add_column("Description")

        for r in pipeline.rules:
            sev_color = "red" if r.severity == "error" else "yellow"
            params_str = ", ".join(f"{k}={v}" for k, v in r.params.items()) or "-"
            table.add_row(
                r.id,
                r.type,
                r.column,
                f"[{sev_color}]{r.severity.upper()}[/{sev_color}]",
                params_str,
                r.description or "-",
            )

        console.print(table)
        console.print(f"\nTotal configured rules: [bold green]{len(pipeline.rules)}[/bold green]")

    except DataSentinelError as e:
        console.print(f"[bold red]Error reading rules:[/bold red] {e}")
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
