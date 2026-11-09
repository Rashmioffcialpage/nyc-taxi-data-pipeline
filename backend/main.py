import os
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://taxi:taxi_local_dev@127.0.0.1:5434/taxi_analytics",
)

app = FastAPI(
    title="NYC Taxi Analytics",
    description="Analytics for retained January–February 2024 taxi trips.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@contextmanager
def database():
    try:
        with psycopg.Connection[dict].connect(
            DATABASE_URL,
            row_factory=dict_row,
            connect_timeout=5,
            options="-c statement_timeout=15000",
        ) as connection:
            yield connection
    except psycopg.Error as error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check that PostgreSQL is running.",
        ) from error


def serialize(row):
    """Convert database dates and decimals into JSON-friendly values."""
    return {
        key: (
            float(value)
            if isinstance(value, Decimal)
            else value.isoformat()
            if isinstance(value, date)
            else value
        )
        for key, value in row.items()
    }


@app.get("/api/health")
def health():
    with database() as connection:
        connection.execute("SELECT 1")

    return {"status": "ok"}


@app.get("/api/summary")
def summary():
    with database() as connection:
        row = connection.execute(
            """
            SELECT
                MIN(pickup_date) AS first_pickup_date,
                MAX(pickup_date) AS last_pickup_date,
                COUNT(*) AS days_with_trips,
                COALESCE(SUM(trip_count), 0) AS trip_count,
                ROUND(
                    SUM(total_distance_miles)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_distance_miles,
                ROUND(
                    SUM(recorded_total_charges_usd),
                    2
                ) AS recorded_total_charges_usd,
                ROUND(
                    SUM(recorded_total_charges_usd)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_recorded_total_usd
            FROM dbt_taxi.daily_trip_summary
            """
        ).fetchone()

    return {
        **serialize(row),
        "scope": "Trips retained under the documented analysis rules.",
        "charges_note": (
            "Recorded total charges are not driver earnings or profit."
        ),
    }


@app.get("/api/trips/daily")
def daily_trips():
    with database() as connection:
        rows = connection.execute(
            """
            SELECT
                pickup_date,
                trip_count,
                total_distance_miles,
                average_distance_miles,
                average_duration_minutes,
                recorded_total_charges_usd,
                average_recorded_total_usd
            FROM dbt_taxi.daily_trip_summary
            ORDER BY pickup_date
            """
        ).fetchall()

    return {"results": [serialize(row) for row in rows]}


@app.get("/api/zones/top")
def top_zones(limit: int = Query(default=10, ge=1, le=50)):
    with database() as connection:
        rows = connection.execute(
            """
            SELECT
                pickup_location_id,
                pickup_borough,
                pickup_zone,
                trip_count,
                average_distance_miles,
                average_duration_minutes,
                recorded_total_charges_usd,
                average_recorded_total_usd
            FROM dbt_taxi.pickup_zone_summary
            ORDER BY trip_count DESC, pickup_location_id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return {"results": [serialize(row) for row in rows]}