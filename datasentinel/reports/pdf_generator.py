"""PDF report generator using ReportLab."""

from __future__ import annotations

import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from datasentinel.core.exceptions import ReportGenerationError
from datasentinel.core.types import PipelineRunResult


class PDFReportGenerator:
    """Generates executive PDF reports using ReportLab."""

    def generate(
        self,
        result: PipelineRunResult,
        output_path: Path,
        source_name: str = "Primary",
    ) -> Path:
        """Render and save PDF report."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36,
            )

            styles = getSampleStyleSheet()

            # Custom typography styles
            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#0f172a"),
            )
            subtitle_style = ParagraphStyle(
                "DocSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#64748b"),
            )
            section_heading = ParagraphStyle(
                "SectionHeading",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#1e293b"),
                spaceBefore=14,
                spaceAfter=6,
            )
            body_style = ParagraphStyle(
                "BodyDark",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor("#334155"),
            )
            header_cell_style = ParagraphStyle(
                "HeaderCell",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=colors.whitesmoke,
            )

            elements = []

            # 1. Header Banner
            elements.append(Paragraph("DataSentinel — Pipeline Quality Report", title_style))
            elements.append(
                Paragraph(
                    f"Pipeline: <b>{html.escape(result.pipeline_name)}</b> | Target Source: {html.escape(source_name)} | "
                    f"Run ID: {html.escape(result.run_id)} | Date: {html.escape(result.timestamp)}",
                    subtitle_style,
                )
            )
            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

            # 2. Executive Metrics Summary Table
            total_rules = result.rules_passed + result.rules_failed + result.rules_warning
            pass_rate = (result.rules_passed / total_rules * 100.0) if total_rules > 0 else 100.0
            total_anomalies = sum(a.total_anomalies for a in result.anomalies)
            drift_status = "DRIFT" if (result.drift_report and result.drift_report.has_drift) else "STABLE"

            metrics_data = [
                ["Quality Pass Rate", "Total Records", "Failed Rules", "Anomalies", "Schema Drift"],
                [
                    f"{pass_rate:.1f}%",
                    f"{result.total_rows:,}",
                    str(result.rules_failed),
                    str(total_anomalies),
                    drift_status,
                ],
            ]

            metric_table = Table(metrics_data, colWidths=[108, 108, 108, 108, 108])
            metric_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 1), (-1, 1), 14),
                    ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#16a34a") if pass_rate >= 90 else colors.HexColor("#dc2626")),
                    ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#16a34a") if result.rules_failed == 0 else colors.HexColor("#dc2626")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                    ("TOPPADDING", (0, 1), (-1, 1), 8),
                ])
            )
            elements.append(metric_table)
            elements.append(Spacer(1, 12))

            # 3. Rule Evaluation Breakdown Table
            elements.append(Paragraph("1. Quality Rules Validation Breakdown", section_heading))

            rule_table_data = [
                [
                    Paragraph("Status", header_cell_style),
                    Paragraph("Rule ID", header_cell_style),
                    Paragraph("Type", header_cell_style),
                    Paragraph("Column", header_cell_style),
                    Paragraph("Failures", header_cell_style),
                    Paragraph("Fail %", header_cell_style),
                    Paragraph("Details", header_cell_style),
                ]
            ]

            for r in result.rule_results:
                status_color = "#16a34a" if r.passed else ("#d97706" if r.status.value == "warning" else "#dc2626")
                status_text = f"<font color='{status_color}'><b>{r.status.value.upper()}</b></font>"
                clean_msg = html.escape(r.message)
                rule_table_data.append([
                    Paragraph(status_text, body_style),
                    Paragraph(f"<b>{html.escape(r.rule_id)}</b>", body_style),
                    Paragraph(html.escape(r.rule_type), body_style),
                    Paragraph(html.escape(r.column), body_style),
                    Paragraph(f"{r.failed_rows}/{r.total_rows}", body_style),
                    Paragraph(f"{r.failure_rate * 100:.1f}%", body_style),
                    Paragraph(clean_msg[:120] + ("..." if len(clean_msg) > 120 else ""), body_style),
                ])

            rule_table = Table(rule_table_data, colWidths=[50, 75, 75, 70, 60, 50, 160])
            rule_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ])
            )
            elements.append(rule_table)
            elements.append(Spacer(1, 12))

            # 4. Statistical Anomaly Table
            if result.anomalies:
                elements.append(Paragraph("2. Statistical Anomaly Detection (Z-Score & IQR)", section_heading))
                anomaly_table_data = [
                    [
                        Paragraph("Column", header_cell_style),
                        Paragraph("Method", header_cell_style),
                        Paragraph("Outliers", header_cell_style),
                        Paragraph("Outlier Rate", header_cell_style),
                        Paragraph("Distribution Metrics", header_cell_style),
                        Paragraph("Top Anomalous Samples", header_cell_style),
                    ]
                ]

                for a in result.anomalies:
                    metrics_str = f"&mu;={a.mean}, &sigma;={a.std}" if a.method == "zscore" else f"Q1={a.q1}, Q3={a.q3}"
                    samples_str = html.escape(", ".join(f"{p.value} (conf={p.score})" for p in a.sample_anomalies[:2])) if a.sample_anomalies else "None"
                    anomaly_table_data.append([
                        Paragraph(f"<b>{html.escape(a.column)}</b>", body_style),
                        Paragraph(html.escape(a.method.upper()), body_style),
                        Paragraph(str(a.total_anomalies), body_style),
                        Paragraph(f"{a.anomaly_rate * 100:.2f}%", body_style),
                        Paragraph(metrics_str, body_style),
                        Paragraph(samples_str, body_style),
                    ])

                anom_table = Table(anomaly_table_data, colWidths=[80, 55, 55, 70, 110, 170])
                anom_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ])
                )
                elements.append(anom_table)
                elements.append(Spacer(1, 12))

            # 5. Schema Drift Table
            if result.drift_report and result.drift_report.diffs:
                elements.append(Paragraph("3. Schema Drift Analysis", section_heading))
                drift_table_data = [
                    [
                        Paragraph("Change Type", header_cell_style),
                        Paragraph("Column", header_cell_style),
                        Paragraph("Baseline", header_cell_style),
                        Paragraph("Current", header_cell_style),
                        Paragraph("Description", header_cell_style),
                    ]
                ]
                for d in result.drift_report.diffs:
                    drift_table_data.append([
                        Paragraph(html.escape(d.drift_type.upper()), body_style),
                        Paragraph(f"<b>{html.escape(d.column_name)}</b>", body_style),
                        Paragraph(html.escape(str(d.baseline_value or "-")), body_style),
                        Paragraph(html.escape(str(d.current_value or "-")), body_style),
                        Paragraph(html.escape(d.message), body_style),
                    ])

                drift_table = Table(drift_table_data, colWidths=[70, 80, 85, 85, 220])
                drift_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elements.append(drift_table)
                elements.append(Spacer(1, 12))

            # Footer
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8, spaceBefore=14))
            elements.append(Paragraph("DataSentinel 0.1.0 • Enterprise Data Quality & Monitoring", subtitle_style))

            doc.build(elements)
            return output_path
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate PDF report at '{output_path}': {e}") from e
