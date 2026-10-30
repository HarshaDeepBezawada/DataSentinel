"""HTML report generator using Jinja2 templates and embedded Chart.js."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from datasentinel.core.exceptions import ReportGenerationError
from datasentinel.core.types import PipelineRunResult
from datasentinel.storage.history import RunHistoryStore


class HTMLReportGenerator:
    """Generates executive-quality HTML data quality reports."""

    def __init__(self, template_dir: Optional[Path] = None) -> None:
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(
        self,
        result: PipelineRunResult,
        output_path: Path,
        source_name: str = "Primary",
        history_store: Optional[RunHistoryStore] = None,
    ) -> Path:
        """Render and save HTML report."""
        try:
            total_rules = result.rules_passed + result.rules_failed + result.rules_warning
            pass_rate = (result.rules_passed / total_rules * 100.0) if total_rules > 0 else 100.0
            total_anomalies = sum(a.total_anomalies for a in result.anomalies)

            history_labels: List[str] = []
            history_pass_rates: List[float] = []
            history_anomalies: List[int] = []

            if history_store:
                recent = history_store.get_recent_runs(result.pipeline_name, limit=8)
                for r in recent:
                    history_labels.append(r["timestamp"][-8:])  # HH:MM:SS
                    r_total = r["rules_passed"] + r["rules_failed"] + r["rules_warning"]
                    r_rate = (r["rules_passed"] / r_total * 100.0) if r_total > 0 else 100.0
                    history_pass_rates.append(round(r_rate, 1))
                    history_anomalies.append(r["anomaly_count"])

            template = self.env.get_template("report_template.html")
            html_content = template.render(
                result=result,
                total_rules=total_rules,
                pass_rate=pass_rate,
                total_anomalies=total_anomalies,
                source_name=source_name,
                history_labels=history_labels,
                history_pass_rates=history_pass_rates,
                history_anomalies=history_anomalies,
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            return output_path
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate HTML report at '{output_path}': {e}") from e
