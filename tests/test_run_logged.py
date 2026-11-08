import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ingestion import run_logged


class LoggedRunTests(unittest.TestCase):
    def test_failed_pipeline_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory)

            process = MagicMock()
            process.stdout = iter([
                "PIPELINE FAILED: simulated test failure\n"
            ])
            process.wait.return_value = 1

            process_context = MagicMock()
            process_context.__enter__.return_value = process

            with (
                patch(
                    "sys.argv",
                    [
                        "run_logged",
                        "--start-month",
                        "2024-01",
                        "--end-month",
                        "2024-02",
                    ],
                ),
                patch.object(run_logged, "LOG_DIR", log_dir),
                patch.object(
                    run_logged.subprocess,
                    "Popen",
                    return_value=process_context,
                ),
                patch("builtins.print"),
            ):
                exit_code = run_logged.main()

            self.assertEqual(exit_code, 1)

            summaries = list(log_dir.glob("*.json"))
            self.assertEqual(len(summaries), 1)

            summary = json.loads(
                summaries[0].read_text(encoding="utf-8")
            )

            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["exit_code"], 1)
            self.assertEqual(summary["start_month"], "2024-01")
            self.assertEqual(summary["end_month"], "2024-02")
            self.assertIn("finished_at", summary)
            self.assertGreaterEqual(summary["duration_seconds"], 0)

            log_file = log_dir / summary["log_file"]
            self.assertIn(
                "simulated test failure",
                log_file.read_text(encoding="utf-8"),
            )
    def test_successful_pipeline_records_success(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory)

            process = MagicMock()
            process.stdout = iter([
                "PIPELINE PASSED in 1.0 seconds\n"
            ])
            process.wait.return_value = 0

            process_context = MagicMock()
            process_context.__enter__.return_value = process

            with (
                patch(
                    "sys.argv",
                    [
                        "run_logged",
                        "--start-month",
                        "2024-01",
                        "--end-month",
                        "2024-02",
                    ],
                ),
                patch.object(run_logged, "LOG_DIR", log_dir),
                patch.object(
                    run_logged.subprocess,
                    "Popen",
                    return_value=process_context,
                ),
                patch("builtins.print"),
            ):
                exit_code = run_logged.main()

            self.assertEqual(exit_code, 0)

            summaries = list(log_dir.glob("*.json"))
            self.assertEqual(len(summaries), 1)

            summary = json.loads(
                summaries[0].read_text(encoding="utf-8")
            )

            self.assertEqual(summary["status"], "passed")
            self.assertEqual(summary["exit_code"], 0)
            self.assertIn("finished_at", summary)
            self.assertGreaterEqual(summary["duration_seconds"], 0)

            log_file = log_dir / summary["log_file"]
            self.assertIn(
                "PIPELINE PASSED",
                log_file.read_text(encoding="utf-8"),
            )

            self.assertFalse(
                list(log_dir.glob("*.json.tmp"))
            )

if __name__ == "__main__":
    unittest.main()