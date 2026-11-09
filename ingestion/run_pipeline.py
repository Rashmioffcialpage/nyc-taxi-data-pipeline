import argparse
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SETUP_SQL_FILES = [
    "001_raw_tables.sql",
    "008_source_month_metadata.sql",
]

TRANSFORM_SQL_FILES = [
    "003_quality_flags.sql",
    "004_analytical_trips.sql",
    "005_quality_checks.sql",
    "006_daily_summary.sql",
    "007_pickup_zone_summary.sql",
]


def parse_month(value: str) -> date:
    try:
        month = datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Use a valid month in YYYY-MM format."
        ) from None

    if month.strftime("%Y-%m") != value:
        raise argparse.ArgumentTypeError(
            "Use YYYY-MM format, such as 2024-02."
        )

    return month


def month_range(start: date, end: date):
    current = start

    while current <= end:
        yield current.strftime("%Y-%m")

        if current == end:
            break

        if current.month == 12:
            current = current.replace(
                year=current.year + 1,
                month=1,
            )
        else:
            current = current.replace(month=current.month + 1)


def run_step(
    name: str,
    command: list[str],
    input_file: Path | None = None,
):
    print(f"\n{'=' * 60}", flush=True)
    print(name, flush=True)
    print(f"{'=' * 60}", flush=True)

    started = time.perf_counter()

    if input_file is None:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=True,
        )
    else:
        with input_file.open("rb") as file:
            subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                stdin=file,
                check=True,
            )

    elapsed = time.perf_counter() - started
    print(f"Completed in {elapsed:.1f} seconds", flush=True)


def run_sql(filename: str):
    run_step(
        f"SQL: {filename}",
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "taxi",
            "-d",
            "taxi_analytics",
        ],
        input_file=PROJECT_ROOT / "sql" / filename,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run the taxi pipeline for an inclusive month range."
    )
    parser.add_argument(
        "--start-month",
        type=parse_month,
        default="2024-01",
        help="First month in YYYY-MM format. Default: 2024-01",
    )
    parser.add_argument(
        "--end-month",
        type=parse_month,
        default=None,
        help="Last month in YYYY-MM format. Defaults to the start month.",
    )
    args = parser.parse_args()

    end_month = args.end_month or args.start_month

    if end_month < args.start_month:
        parser.error("--end-month must not precede --start-month")

    months = list(month_range(args.start_month, end_month))

        # Validate required inputs before changing the database.
    required_files = [
        PROJECT_ROOT / ".venv-dbt/bin/dbt",
        PROJECT_ROOT / "dbt/dbt_project.yml",
        PROJECT_ROOT / "dbt/profiles.yml",
        PROJECT_ROOT / "compose.yaml",
        PROJECT_ROOT / "data/raw/taxi_zone_lookup.csv",
        PROJECT_ROOT / "ingestion/load_zones.py",
        PROJECT_ROOT / "ingestion/load_trips.py",
        *[
            PROJECT_ROOT
            / "data"
            / "raw"
            / f"yellow_tripdata_{month}.parquet"
            for month in months
        ],
        *[
            PROJECT_ROOT / "sql" / filename
            for filename in SETUP_SQL_FILES + TRANSFORM_SQL_FILES
        ],
    ]
    missing = [
        str(path)
        for path in required_files
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Required files are missing:\n" + "\n".join(missing)
        )

    started = time.perf_counter()
    print(f"Requested months: {', '.join(months)}", flush=True)

    run_step(
        "Check database readiness",
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "pg_isready",
            "-U",
            "taxi",
            "-d",
            "taxi_analytics",
        ],
    )

    # Create tables and apply metadata migration before importing.
    for filename in SETUP_SQL_FILES:
        run_sql(filename)

    run_step(
        "Load taxi zones",
        [sys.executable, "-m", "ingestion.load_zones"],
    )

    for month in months:
        run_step(
            f"Load trips: {month}",
            [
                sys.executable,
                "-m",
                "ingestion.load_trips",
                "--month",
                month,
            ],
        )

    # Rebuild views and validate all loaded months.
    for filename in TRANSFORM_SQL_FILES:
        run_sql(filename)
    run_step(
        "Build and test dbt models",
        [
            str(PROJECT_ROOT / ".venv-dbt" / "bin" / "dbt"),
            "build",
            "--project-dir",
            str(PROJECT_ROOT / "dbt"),
            "--profiles-dir",
            str(PROJECT_ROOT / "dbt"),
        ],
    )
    elapsed = time.perf_counter() - started
    print(f"\nPIPELINE PASSED in {elapsed:.1f} seconds", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(
            f"\nPIPELINE FAILED: command exited "
            f"with code {error.returncode}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}", file=sys.stderr)
        sys.exit(1)