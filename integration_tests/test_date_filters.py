import json
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8003"

ENDPOINTS = (
    "/api/summary",
    "/api/trips/daily",
    "/api/zones/top",
)


def get_api(path, **parameters):
    query = urlencode(parameters)
    url = f"{BASE_URL}{path}"

    if query:
        url += f"?{query}"

    try:
        with urlopen(url, timeout=20) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.load(error)
        finally:
            error.close()


class DateFilterTests(unittest.TestCase):
    def test_january_summary_and_daily_reconciliation(self):
        parameters = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        }

        status, summary = get_api("/api/summary", **parameters)
        daily_status, daily = get_api(
            "/api/trips/daily", **parameters
        )

        self.assertEqual(status, 200)
        self.assertEqual(daily_status, 200)
        self.assertEqual(summary["trip_count"], 2_868_179)
        self.assertEqual(summary["days_with_trips"], 31)
        self.assertAlmostEqual(
            summary["recorded_total_charges_usd"],
            78_406_797.55,
            places=2,
        )

        rows = daily["results"]
        self.assertEqual(len(rows), 31)

        self.assertTrue(
            all(
                "2024-01-01" <= row["pickup_date"] <= "2024-01-31"
                for row in rows
            )
        )

        self.assertEqual(
            sum(row["trip_count"] for row in rows),
            summary["trip_count"],
        )
        self.assertAlmostEqual(
            sum(row["recorded_total_charges_usd"] for row in rows),
            summary["recorded_total_charges_usd"],
            places=2,
        )

    def test_single_day_is_inclusive(self):
        parameters = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
        }

        status, summary = get_api("/api/summary", **parameters)
        daily_status, daily = get_api(
            "/api/trips/daily", **parameters
        )

        self.assertEqual(status, 200)
        self.assertEqual(daily_status, 200)
        self.assertEqual(summary["days_with_trips"], 1)
        self.assertEqual(summary["trip_count"], 75_449)
        self.assertEqual(len(daily["results"]), 1)
        self.assertEqual(
            daily["results"][0]["pickup_date"], "2024-01-01"
        )

    def test_january_zone_rankings_use_filtered_data(self):
        status, result = get_api(
            "/api/zones/top",
            start_date="2024-01-01",
            end_date="2024-01-31",
            limit=3,
        )

        self.assertEqual(status, 200)

        rows = result["results"]
        self.assertEqual(len(rows), 3)

        self.assertEqual(
            [
                (row["pickup_location_id"], row["trip_count"])
                for row in rows
            ],
            [
                (161, 140_079),
                (237, 140_069),
                (132, 138_337),
            ],
        )

    def test_empty_period(self):
        parameters = {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }

        status, summary = get_api("/api/summary", **parameters)

        self.assertEqual(status, 200)
        self.assertEqual(summary["trip_count"], 0)
        self.assertEqual(summary["days_with_trips"], 0)
        self.assertEqual(summary["recorded_total_charges_usd"], 0)
        self.assertIsNone(summary["first_pickup_date"])
        self.assertIsNone(summary["last_pickup_date"])
        self.assertIsNone(summary["average_distance_miles"])
        self.assertIsNone(summary["average_recorded_total_usd"])

        for endpoint in ("/api/trips/daily", "/api/zones/top"):
            with self.subTest(endpoint=endpoint):
                status, result = get_api(endpoint, **parameters)
                self.assertEqual(status, 200)
                self.assertEqual(result["results"], [])

    def test_reversed_dates_rejected(self):
        for endpoint in ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                status, result = get_api(
                    endpoint,
                    start_date="2024-02-01",
                    end_date="2024-01-01",
                )

                self.assertEqual(status, 422)
                self.assertIn("detail", result)

    def test_invalid_dates_rejected(self):
        for endpoint in ENDPOINTS:
            for parameter in ("start_date", "end_date"):
                with self.subTest(
                    endpoint=endpoint,
                    parameter=parameter,
                ):
                    status, result = get_api(
                        endpoint,
                        **{parameter: "2024-02-30"},
                    )

                    self.assertEqual(status, 422)
                    self.assertIn("detail", result)

    def test_open_boundaries_match_explicit_ranges(self):
        for endpoint in ENDPOINTS:
            for open_parameters, explicit_parameters in (
                (
                    {"end_date": "2024-01-31"},
                    {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-31",
                    },
                ),
                (
                    {"start_date": "2024-02-01"},
                    {
                        "start_date": "2024-02-01",
                        "end_date": "2024-02-29",
                    },
                ),
            ):
                with self.subTest(
                    endpoint=endpoint,
                    parameters=open_parameters,
                ):
                    status, result = get_api(
                        endpoint, **open_parameters
                    )
                    expected_status, expected = get_api(
                        endpoint, **explicit_parameters
                    )

                    self.assertEqual(status, 200)
                    self.assertEqual(expected_status, 200)
                    self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()