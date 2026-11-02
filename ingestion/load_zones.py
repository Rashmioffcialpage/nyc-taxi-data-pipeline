import csv
import os
from pathlib import Path

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ZONE_FILE = PROJECT_ROOT / "data/raw/taxi_zone_lookup.csv"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://taxi:taxi_local_dev@127.0.0.1:5434/taxi_analytics",
)


def main():
    with ZONE_FILE.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "LocationID", "Borough", "Zone", "service_zone"
        }

        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError("Zone CSV is missing required columns.")

        rows = [
            (
                int(row["LocationID"]),
                row["Borough"],
                row["Zone"],
                row["service_zone"],
            )
            for row in reader
        ]

    location_ids = [row[0] for row in rows]

    if not rows:
        raise ValueError("Zone CSV is empty.")

    if len(location_ids) != len(set(location_ids)):
        raise ValueError("Zone CSV contains duplicate location IDs.")

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO raw.taxi_zones (
                    location_id,
                    borough,
                    zone,
                    service_zone
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (location_id) DO UPDATE SET
                    borough = EXCLUDED.borough,
                    zone = EXCLUDED.zone,
                    service_zone = EXCLUDED.service_zone
                """,
                rows,
            )

            cursor.execute("SELECT COUNT(*) FROM raw.taxi_zones")
            result = cursor.fetchone()

            if result is None:
                raise RuntimeError("Unable to verify zone count.")

            total = result[0]

    print(f"CSV zones read: {len(rows):,}")
    print(f"Zones inserted or updated: {len(rows):,}")
    print(f"Total database zones: {total:,}")


if __name__ == "__main__":
    main()