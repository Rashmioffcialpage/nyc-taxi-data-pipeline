import os
import subprocess
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="nyc_taxi_pipeline",
    description="Run the local taxi ingestion, SQL checks, and dbt build.",
    schedule=None,
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    tags=["taxi", "postgres", "dbt"],
)
def taxi_pipeline():

    @task(
        task_id="run_logged_pipeline",
        retries=2,
        retry_delay=timedelta(minutes=1),
        execution_timeout=timedelta(minutes=30),
    )
    def run_pipeline():
        project_root = Path(
            "/Users/rashmidragon/Desktop/nyc-taxi-data-pipeline"
        )

        pipeline_python = project_root / ".venv/bin/python"

        if not pipeline_python.is_file():
            raise FileNotFoundError(
                f"Pipeline Python not found: {pipeline_python}"
            )

        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"

        # Include common Docker CLI locations on macOS.
        environment["PATH"] = os.pathsep.join([
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/Applications/Docker.app/Contents/Resources/bin",
            environment.get("PATH", ""),
        ])

        subprocess.run(
            [
                str(pipeline_python),
                "-u",
                "-m",
                "ingestion.run_logged",
                "--start-month",
                "2024-01",
                "--end-month",
                "2024-02",
            ],
            cwd=project_root,
            env=environment,
            check=True,
        )

    run_pipeline()


taxi_pipeline()