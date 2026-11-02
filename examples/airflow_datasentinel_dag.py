"""Apache Airflow DAG demonstrating DataSentinel as a Production Circuit Breaker.

Architecture Pattern: Circuit Breaker Quality Gate
--------------------------------------------------
In enterprise data engineering (e.g., Airbnb, Spotify), data platforms must
verify data freshness, schema integrity, and statistical anomalies BEFORE
loading raw staging datasets into downstream analytical warehouses.

DAG Execution Flow:
    [Extract Source Data]
             │
             ▼
    [DataSentinel Quality Gate]  <--- Halts DAG immediately if violations detected!
             │ (Exit Code 0)
             ▼
    [Transform (dbt / Spark)]
             │
             ▼
    [Load Production Warehouse / Dashboards]
"""

from __future__ import annotations

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email": ["data-alerts@example.com"],
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="ecommerce_pipeline_with_datasentinel_gate",
    default_args=default_args,
    description="Daily retail order processing pipeline with automated quality gate",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["quality", "datasentinel", "production"],
) as dag:

    start_task = EmptyOperator(task_id="start_pipeline")

    # 1. Ingest raw landing files from source connectors
    extract_landing_data = BashOperator(
        task_id="extract_landing_orders",
        bash_command="echo 'Extracting raw transactional orders from landing bucket...'",
    )

    # 2. DataSentinel Automated Quality & Anomaly Gate (Circuit Breaker)
    # If any quality check fails or schema drift occurs, DataSentinel exits with code 1,
    # causing Airflow to halt the pipeline and prevent dirty data from reaching BI dashboards.
    datasentinel_quality_gate = BashOperator(
        task_id="datasentinel_data_quality_gate",
        bash_command=(
            "datasentinel validate config/ecommerce_orders.yaml "
            "--export-json /tmp/orders_run_metrics.json "
            "--quiet"
        ),
    )

    # 3. Downstream transformation (only executes if DataSentinel passes)
    transform_warehouse_models = BashOperator(
        task_id="dbt_transform_models",
        bash_command="echo 'Running downstream dimensional modeling and aggregations...'",
    )

    end_task = EmptyOperator(task_id="end_pipeline")

    # Pipeline Dependency Graph
    (
        start_task
        >> extract_landing_data
        >> datasentinel_quality_gate
        >> transform_warehouse_models
        >> end_task
    )
