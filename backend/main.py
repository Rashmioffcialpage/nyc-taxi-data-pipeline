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
    description="Analytics for retained yellow taxi trips.",
    version="0.2.0",
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
            detail="Could not query the database. Check the API server logs.",
        ) from error


def serialize(row):
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


def date_filter(start_date, end_date):
    """Build an inclusive date filter using bound SQL parameters."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must not be later than end_date.",
        )

    conditions = []
    parameters = []

    if start_date is not None:
        conditions.append("pickup_date >= %s")
        parameters.append(start_date)

    if end_date is not None:
        conditions.append("pickup_date <= %s")
        parameters.append(end_date)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where, parameters


@app.get("/api/health")
def health():
    with database() as connection:
        connection.execute("SELECT 1")

    return {"status": "ok"}


@app.get("/api/summary")
def summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    where, parameters = date_filter(start_date, end_date)

    with database() as connection:
        row = connection.execute(
            f"""
            SELECT
                MIN(pickup_date) AS first_pickup_date,
                MAX(pickup_date) AS last_pickup_date,
                COUNT(*) AS days_with_trips,
                COALESCE(SUM(trip_count), 0)::bigint AS trip_count,
                ROUND(
                    SUM(total_distance_miles)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_distance_miles,
                COALESCE(
                    ROUND(SUM(recorded_total_charges_usd), 2),
                    0
                ) AS recorded_total_charges_usd,
                ROUND(
                    SUM(recorded_total_charges_usd)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_recorded_total_usd
            FROM dbt_taxi.daily_trip_summary
            {where}
            """,
            parameters,
        ).fetchone()

    return {
        **serialize(row),
        "scope": "Trips retained under the documented analysis rules.",
        "charges_note": (
            "Recorded total charges are not driver earnings or profit."
        ),
    }


@app.get("/api/trips/daily")
def daily_trips(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    where, parameters = date_filter(start_date, end_date)

    with database() as connection:
        rows = connection.execute(
            f"""
            SELECT
                pickup_date,
                trip_count,
                total_distance_miles,
                average_distance_miles,
                average_duration_minutes,
                recorded_total_charges_usd,
                average_recorded_total_usd
            FROM dbt_taxi.daily_trip_summary
            {where}
            ORDER BY pickup_date
            """,
            parameters,
        ).fetchall()

    return {"results": [serialize(row) for row in rows]}


@app.get("/api/zones/top")
def top_zones(
    limit: int = Query(default=10, ge=1, le=50),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    where, parameters = date_filter(start_date, end_date)

    with database() as connection:
        rows = connection.execute(
            f"""
            SELECT
                pickup_location_id,
                pickup_borough,
                pickup_zone,
                SUM(trip_count)::bigint AS trip_count,
                ROUND(
                    SUM(total_distance_miles)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_distance_miles,
                ROUND(
                    SUM(total_duration_minutes)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_duration_minutes,
                ROUND(
                    SUM(recorded_total_charges_usd),
                    2
                ) AS recorded_total_charges_usd,
                ROUND(
                    SUM(recorded_total_charges_usd)
                    / NULLIF(SUM(trip_count), 0),
                    2
                ) AS average_recorded_total_usd
            FROM dbt_taxi.daily_pickup_zone_summary
            {where}
            GROUP BY
                pickup_location_id,
                pickup_borough,
                pickup_zone
            ORDER BY trip_count DESC, pickup_location_id
            LIMIT %s
            """,
            [*parameters, limit],
        ).fetchall()

    return {"results": [serialize(row) for row in rows]}