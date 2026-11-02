import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ingestion.run_pipeline import parse_month


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "logs"


def main():
    parser = argparse.ArgumentParser(
        description="Run the taxi pipeline and save a run summary."
    )
    parser.add_argument(
        "--start-month",
        type=parse_month,
        default="2024-01",
    )
    parser.add_argument(
        "--end-month",
        type=parse_month,
        default=None,
    )
    args = parser.parse_args()

    end_month = args.end_month or args.start_month

    if end_month < args.start_month:
        parser.error("--end-month must not precede --start-month")

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    log_path = LOG_DIR / f"{run_id}.log"
    summary_path = LOG_DIR / f"{run_id}.json"

    summary = {
        "run_id": run_id,
        "start_month": args.start_month.strftime("%Y-%m"),
        "end_month": end_month.strftime("%Y-%m"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "log_file": log_path.name,
    }

    def save_summary():
        temporary = summary_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(summary_path)

    save_summary()
    started = time.perf_counter()
    exit_code = 1

    command = [
        sys.executable,
        "-u",
        "-m",
        "ingestion.run_pipeline",
        "--start-month",
        summary["start_month"],
        "--end-month",
        summary["end_month"],
    ]

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            with subprocess.Popen(
                command,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            ) as process:
                if process.stdout is None:
                    raise RuntimeError("Unable to capture pipeline output.")

                for line in process.stdout:
                    print(line, end="", flush=True)
                    log_file.write(line)
                    log_file.flush()

                exit_code = process.wait()

        summary["status"] = "passed" if exit_code == 0 else "failed"

    except KeyboardInterrupt:
        exit_code = 130
        summary["status"] = "interrupted"

    except Exception as error:
        summary["status"] = "failed"
        summary["error"] = str(error)
        print(f"Logging runner failed: {error}", file=sys.stderr)

    finally:
        summary["finished_at"] = datetime.now(timezone.utc).isoformat()
        summary["duration_seconds"] = round(
            time.perf_counter() - started, 2
        )
        summary["exit_code"] = exit_code
        save_summary()

        print(f"\nRun summary: {summary_path}")
        print(f"Console log: {log_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())