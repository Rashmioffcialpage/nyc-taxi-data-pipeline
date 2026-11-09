import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8003"


def get_api(path):
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.load(error)
        finally:
            error.close()


class DashboardApiTests(unittest.TestCase):
    def test_health(self):
        status, result = get_api("/api/health")

        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "ok")

    def test_verified_january_february_summary(self):
        status, result = get_api("/api/summary")

        self.assertEqual(status, 200)
        self.assertEqual(result["first_pickup_date"], "2024-01-01")
        self.assertEqual(result["last_pickup_date"], "2024-02-29")
        self.assertEqual(result["days_with_trips"], 60)
        self.assertEqual(result["trip_count"], 5_768_183)
        self.assertAlmostEqual(
            result["recorded_total_charges_usd"],
            157_373_105.81,
            places=2,
        )

    def test_daily_counts_reconcile_with_summary(self):
        summary_status, summary = get_api("/api/summary")
        daily_status, daily = get_api("/api/trips/daily")

        self.assertEqual(summary_status, 200)
        self.assertEqual(daily_status, 200)

        rows = daily["results"]
        dates = [row["pickup_date"] for row in rows]

        self.assertEqual(len(rows), summary["days_with_trips"])
        self.assertEqual(len(dates), len(set(dates)))
        self.assertEqual(dates, sorted(dates))
        self.assertTrue(all(row["trip_count"] > 0 for row in rows))
        self.assertEqual(
            sum(row["trip_count"] for row in rows),
            summary["trip_count"],
        )

        self.assertAlmostEqual(
            sum(row["recorded_total_charges_usd"] for row in rows),
            summary["recorded_total_charges_usd"],
            places=2,
        )

    def test_summary_averages_use_trip_weights(self):
        _, summary = get_api("/api/summary")
        status, daily = get_api("/api/trips/daily")

        self.assertEqual(status, 200)

        rows = daily["results"]
        trips = sum(row["trip_count"] for row in rows)
        self.assertGreater(trips, 0)

        expected_distance = (
            sum(row["total_distance_miles"] for row in rows) / trips
        )
        expected_charge = (
            sum(row["recorded_total_charges_usd"] for row in rows)
            / trips
        )

        self.assertAlmostEqual(
            summary["average_distance_miles"],
            expected_distance,
            delta=0.0051,
        )
        self.assertAlmostEqual(
            summary["average_recorded_total_usd"],
            expected_charge,
            delta=0.0051,
        )

    def test_top_zones_order_and_limit(self):
        status, result = get_api("/api/zones/top?limit=3")

        self.assertEqual(status, 200)

        rows = result["results"]
        self.assertEqual(len(rows), 3)

        expected_order = sorted(
            rows,
            key=lambda row: (
                -row["trip_count"],
                row["pickup_location_id"],
            ),
        )
        self.assertEqual(rows, expected_order)

        ids = [row["pickup_location_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))

        self.assertEqual(rows[0]["pickup_zone"], "Midtown Center")
        self.assertEqual(rows[0]["trip_count"], 283_373)

    def test_zone_limit_returns_consistent_prefix(self):
        small_status, small = get_api("/api/zones/top?limit=3")
        large_status, large = get_api("/api/zones/top?limit=10")

        self.assertEqual(small_status, 200)
        self.assertEqual(large_status, 200)
        self.assertEqual(len(large["results"]), 10)
        self.assertEqual(small["results"], large["results"][:3])

    def test_invalid_zone_limits_rejected(self):
        for limit in ("0", "-1", "51", "abc", "1.5"):
            with self.subTest(limit=limit):
                status, result = get_api(
                    f"/api/zones/top?limit={limit}"
                )

                self.assertEqual(status, 422)
                self.assertIn("detail", result)


if __name__ == "__main__":
    unittest.main()