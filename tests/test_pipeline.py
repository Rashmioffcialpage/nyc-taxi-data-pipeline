import argparse
import subprocess
import unittest
from datetime import date
from unittest.mock import patch
import tempfile
from pathlib import Path

from ingestion.run_pipeline import main
from ingestion.run_pipeline import (
    month_range,
    parse_month,
    run_step,
)


class PipelineTests(unittest.TestCase):
    def test_valid_month(self):
        self.assertEqual(
            parse_month("2024-02"),
            date(2024, 2, 1),
        )

    def test_invalid_months_rejected(self):
        for value in [
            "2024-00",
            "2024-13",
            "2024-2",
            "February",
            "2024-02-01",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    parse_month(value)

    def test_single_month_range(self):
        self.assertEqual(
            list(month_range(date(2024, 2, 1), date(2024, 2, 1))),
            ["2024-02"],
        )

    def test_range_includes_both_endpoints(self):
        self.assertEqual(
            list(month_range(date(2024, 1, 1), date(2024, 3, 1))),
            ["2024-01", "2024-02", "2024-03"],
        )

    def test_range_crosses_year_boundary(self):
        self.assertEqual(
            list(month_range(date(2024, 12, 1), date(2025, 2, 1))),
            ["2024-12", "2025-01", "2025-02"],
        )

    @patch("ingestion.run_pipeline.subprocess.run")
    def test_command_failure_propagates(self, mock_run):
        command = ["example-command"]
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
        )

        with self.assertRaises(subprocess.CalledProcessError):
            run_step("Expected failure test", command)

        self.assertTrue(mock_run.call_args.kwargs["check"])
    def test_reversed_range_rejected_before_commands(self):
        arguments = [
            "run_pipeline",
            "--start-month",
            "2024-03",
            "--end-month",
            "2024-01",
        ]

        with (
            patch("sys.argv", arguments),
            patch("sys.stderr"),
            patch(
                "ingestion.run_pipeline.subprocess.run"
            ) as mock_run,
        ):
            with self.assertRaises(SystemExit) as caught:
                main()

            self.assertEqual(caught.exception.code, 2)
            mock_run.assert_not_called()

    def test_missing_files_rejected_before_commands(self):
        arguments = [
            "run_pipeline",
            "--start-month",
            "2024-01",
        ]

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch("sys.argv", arguments),
                patch(
                    "ingestion.run_pipeline.PROJECT_ROOT",
                    Path(directory),
                ),
                patch(
                    "ingestion.run_pipeline.subprocess.run"
                ) as mock_run,
            ):
                with self.assertRaises(FileNotFoundError) as caught:
                    main()

                self.assertIn(
                    "yellow_tripdata_2024-01.parquet",
                    str(caught.exception),
                )
                mock_run.assert_not_called()

if __name__ == "__main__":
    unittest.main()