import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str], input_file=None):
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
    path = PROJECT_ROOT / "sql" / filename

    if not path.is_file():
        raise FileNotFoundError(f"Missing SQL file: {path}")

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
        input_file=path,
    )


def main():
    started = time.perf_counter()

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

    run_sql("001_raw_tables.sql")

    run_step(
        "Load taxi zones",
        [sys.executable, "-m", "ingestion.load_zones"],
    )

    run_step(
        "Load trip records",
        [sys.executable, "-m", "ingestion.load_trips"],
    )

    run_sql("003_quality_flags.sql")
    run_sql("004_analytical_trips.sql")
    run_sql("005_quality_checks.sql")
    run_sql("006_daily_summary.sql")
    run_sql("007_pickup_zone_summary.sql")

    elapsed = time.perf_counter() - started

    print(
        f"\nPIPELINE PASSED in {elapsed:.1f} seconds",
        flush=True,
    )


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