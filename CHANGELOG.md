# Changelog

All notable changes to the **DataSentinel** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-30

### Added
- **Core Architecture & Dataset Interface**:
  - `DataSet` wrapper providing unified in-memory and chunked streaming access to tabular data.
  - Domain types and Pydantic v2 schemas for fingerprints, drift diffs, rule results, and anomalies.
  - Comprehensive custom domain exceptions (`ConnectorError`, `RuleValidationError`, `SchemaDriftError`, etc.).
- **Multi-Source Connector Registry**:
  - Abstract `BaseConnector` enforcing common lifecycle and streaming interface.
  - Decorator-based `ConnectorRegistry` implementing the Open/Closed Principle.
  - Concrete adapters: CSV, Excel (.xlsx/.xls), JSON (flat and nested JSONPath), SQLite, PostgreSQL (via SQLAlchemy 2.0), and REST API with pagination.
  - Secure credential expansion from environment variables (`${VAR}` and `env:VAR`).
- **Declarative YAML Rule Engine**:
  - Validated by Pydantic v2 models without hardcoded Python thresholds.
  - Executable rules: `null_check`, `unique_check`, `range`, `regex`, and `foreign_key` referential integrity.
  - `RuleExecutor` with Rich animated progress bar.
- **Schema Baseline & Drift Detection**:
  - `SchemaFingerprintGenerator` capturing column definitions, nullability, and unique metrics.
  - `SchemaRegistry` managing baseline storage in JSON.
  - `SchemaDriftDetector` reporting added, removed, type-changed, and nullability-changed diffs.
- **Statistical Anomaly Detection (Memory-Efficient)**:
  - Streaming Z-Score outlier detection ($|z| > \text{threshold}$, default 3.0).
  - Streaming IQR Tukey fence outlier detection ($[Q_1 - 1.5 \times IQR, Q_3 + 1.5 \times IQR]$).
  - Scaled confidence scores $[0.5, 1.0]$.
  - Two-pass chunked streaming designed for 500,000+ row scalability.
- **Observability, Reports & Storage**:
  - SQLite-backed `RunHistoryStore` capturing execution trends over time.
  - Executive Jinja2 HTML reports with embedded CDN Chart.js (pass rate donut, historical trend lines).
  - Publication-quality ReportLab vector PDF report generation with headers, metrics, and tables.
  - Privacy-preserving alert notifiers for SMTP email and Slack webhooks (strictly zero raw customer records).
- **Automation & CLI**:
  - APScheduler integration with cron syntax and overlap protection (`coalesce=True`, `max_instances=1`).
  - Typer CLI with Rich styled outputs for `validate`, `report`, `compare-schemas`, `schedule`, and `list-rules`.
- **Testing & Quality Assurance**:
  - 46 unit, integration, and Hypothesis property-based tests.
  - Line coverage exceeding 83% (above 75% requirement).
  - Zero mypy strict mode type errors across 45 source files.
