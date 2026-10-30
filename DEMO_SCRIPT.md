# 🎬 DataSentinel — 5-Minute Project Demonstration Video Script

This script provides an exact, second-by-second walkthrough for recording the 5-minute project demonstration required for the **Code A Nova Internship Project 4 (DataSentinel)**.

---

## ⏱️ Video Outline & Timing Breakdown (Total: 5:00)

| Timestamp | Segment | Visual / Action | Key Speaking Points |
|---|---|---|---|
| **0:00 - 0:35** | 1. Introduction | Title slide / webcam | Project vision, problem statement, enterprise importance |
| **0:35 - 1:10** | 2. Architecture & Tech Stack | Mermaid diagram / README | Layered architecture, plugin registry, Open/Closed Principle |
| **1:10 - 1:45** | 3. Declarative YAML Rules | VS Code opening `config/*.yaml` | Zero hardcoded thresholds, Pydantic v2 validation |
| **1:45 - 2:30** | 4. CLI & Pipeline Validation | Terminal executing `datasentinel validate` | Rich styled output, real violations caught (null, unique, range, regex, FK) |
| **2:30 - 3:15** | 5. Schema Drift & Anomaly Detection | Terminal executing `compare-schemas` & 500k benchmark | Structural drift detection, streaming Z-score & IQR for 500,000 rows |
| **3:15 - 4:05** | 6. Executive HTML & PDF Reports | Browser showing HTML + PDF viewer | Interactive Chart.js charts, historical trends, ReportLab PDF export |
| **4:05 - 4:40** | 7. Test Suite & Type Safety | Terminal running `pytest` & `mypy` | 47 passed tests, >83% coverage, Hypothesis property tests, zero mypy errors |
| **4:40 - 5:00** | 8. Conclusion & Deliverables | GitHub repo overview / Summary | Package installability, wheel distribution, wrap-up |

---

## 🎙️ Step-by-Step Recording Walkthrough

### Part 1: Introduction (0:00 - 0:35)
- **Voiceover:**
  > *"Hello everyone! Welcome to this demonstration of DataSentinel — an enterprise automated data quality and pipeline monitoring platform built for the Code A Nova Python Development Internship."*
  > *"In modern data platforms at companies like Netflix, Airbnb, and Spotify, silent data corruption ruins machine learning models, breaks dashboards, and costs millions. DataSentinel acts as an automated firewall for data pipelines, connecting to diverse sources, validating data against declarative rules, detecting schema drift, catching statistical anomalies, and generating executive reports without leaking private customer data."*

---

### Part 2: Architecture & Extensibility (0:35 - 1:10)
- **Screen:** Show the architecture diagram from `README.md`.
- **Voiceover:**
  > *"DataSentinel is designed around the Open/Closed Principle with clean separation of concerns. The Connector Registry provides an abstract base interface with concrete adapters for CSV, Excel (.xlsx/.xls), JSON with nested dot-paths, SQLite, PostgreSQL via SQLAlchemy 2.0, and paginated REST APIs. Database credentials and API tokens are resolved securely from environment variables."*

---

### Part 3: Declarative YAML Rule Engine (1:10 - 1:45)
- **Screen:** Open `config/ecommerce_orders.yaml` in VS Code.
- **Voiceover:**
  > *"All rules and validation thresholds are defined strictly in declarative YAML files validated at load time by Pydantic v2. There are zero hardcoded thresholds in Python source code."*
  > *"Here we see our e-commerce configuration with null checks, uniqueness constraints on order IDs, regex email validation, numeric range checks on order amounts, and referential integrity against sanctioned payment gateways."*

---

### Part 4: CLI Inspection & Validation (1:45 - 2:30)
- **Terminal Action 1:** Run `list-rules`:
  ```bash
  datasentinel list-rules config/ecommerce_orders.yaml
  ```
- **Voiceover:**
  > *"DataSentinel provides an intuitive CLI powered by Typer and Rich. Using `list-rules`, we can inspect all active quality checks in a clean formatted table."*

- **Terminal Action 2:** Run `validate`:
  ```bash
  datasentinel validate config/ecommerce_orders.yaml
  ```
- **Voiceover:**
  > *"Now we execute validation against our real-world dataset. The Rich progress bar tracks evaluation in real-time, followed by an executive summary table. DataSentinel caught every intentional violation: missing customer emails, duplicate order IDs, malformed email patterns, negative and extreme prices, and unauthorized payment methods."*

---

### Part 5: Schema Drift & Anomaly Detection (2:30 - 3:15)
- **Terminal Action 1:** Run `compare-schemas`:
  ```bash
  datasentinel compare-schemas data/ecommerce_orders_drifted.csv --baseline data/ecommerce_orders.csv
  ```
- **Voiceover:**
  > *"DataSentinel fingerprints schemas and monitors for drift. Running `compare-schemas` immediately pinpoints that `payment_method` was removed, a new `shipping_country` column was added, and `total_amount` changed type from float to string."*

- **Voiceover (Anomaly Detection & 500k Scale):**
  > *"For statistical anomaly detection, DataSentinel combines Z-score outlier detection (|z| > 3.0) and Tukey IQR fences, computing normalized confidence scores from 0.5 to 1.0. Most importantly, it uses a two-pass chunked streaming algorithm that processes datasets of up to 500,000 rows without loading all data into memory simultaneously, keeping memory consumption strictly under control."*

---

### Part 6: Executive HTML & PDF Reports (3:15 - 4:05)
- **Terminal Action:** Generate reports:
  ```bash
  datasentinel report config/ecommerce_orders.yaml --html reports/ecommerce_orders_report.html --pdf reports/ecommerce_orders_report.pdf
  ```
- **Screen:** Open `reports/ecommerce_orders_report.html` in Chrome/Firefox.
- **Voiceover:**
  > *"DataSentinel generates executive-ready visual reports. The HTML dashboard features a dark-mode theme, executive KPI cards, an interactive Chart.js pass-rate donut chart, and a multi-run historical quality trend line retrieved from the SQLite run history store. It renders flawlessly in Chrome, Firefox, and Safari without any frontend framework overhead."*

- **Screen:** Open `reports/ecommerce_orders_report.pdf` in PDF viewer.
- **Voiceover:**
  > *"Simultaneously, DataSentinel generates a publication-quality vector PDF report using ReportLab with clean typography, metric blocks, color-coded status badges, and multi-page table formatting."*

---

### Part 7: Test Suite & Type Safety (4:05 - 4:40)
- **Terminal Action 1:** Run `pytest`:
  ```bash
  pytest
  ```
- **Voiceover:**
  > *"Quality assurance is paramount. The automated test suite executes 47 comprehensive tests in just 7 seconds, achieving over 83% line coverage — well exceeding the 75% internship requirement. It includes property-based testing with Hypothesis to mathematically verify anomaly calculation invariants."*

- **Terminal Action 2:** Run `mypy`:
  ```bash
  mypy datasentinel
  ```
- **Voiceover:**
  > *"Running mypy in strict mode confirms zero type errors across all 45 source files, guaranteeing 100% full type safety."*

---

### Part 8: Conclusion & Packaging (4:40 - 5:00)
- **Terminal Action:** Show wheel package in `dist/`:
  ```bash
  Get-ChildItem -Path dist
  ```
- **Voiceover:**
  > *"DataSentinel is fully packaged as a standard pip-installable wheel, includes a CI/CD GitHub Actions pipeline, SQLite run history, and privacy-preserving alerts for Slack and SMTP. All Code A Nova Project 4 requirements have been 200% fulfilled. Thank you for watching!"*
