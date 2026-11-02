BEGIN;

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE VIEW staging.yellow_trips_quality AS
SELECT
    t.*,

    EXTRACT(
        EPOCH FROM (dropoff_datetime - pickup_datetime)
    ) / 60.0 AS trip_duration_minutes,

    (
        pickup_datetime IS NULL
        OR dropoff_datetime IS NULL
    ) AS missing_trip_time,

    COALESCE(
        dropoff_datetime <= pickup_datetime,
        FALSE
    ) AS nonpositive_duration,

    COALESCE(
        pickup_datetime < TIMESTAMP '2024-01-01'
        OR pickup_datetime >= TIMESTAMP '2024-02-01',
        FALSE
    ) AS pickup_outside_source_month,

    (
        trip_distance IS NULL
    ) AS missing_distance,

    COALESCE(
        trip_distance <= 0,
        FALSE
    ) AS nonpositive_distance,

    COALESCE(
        fare_amount < 0 OR total_amount < 0,
        FALSE
    ) AS negative_charge,

    (
        fare_amount IS NULL
        OR total_amount IS NULL
    ) AS missing_charge,

    (
        passenger_count IS NULL
    ) AS missing_passenger_count,

    COALESCE(
        passenger_count = 0,
        FALSE
    ) AS zero_passenger_count,

    -- Review thresholds, not established data-error rules.
    COALESCE(
        trip_distance > 100,
        FALSE
    ) AS distance_over_100_miles,

    COALESCE(
        dropoff_datetime - pickup_datetime > INTERVAL '6 hours',
        FALSE
    ) AS duration_over_6_hours

FROM raw.yellow_trips AS t
WHERE source_file = 'yellow_tripdata_2024-01.parquet';

COMMIT;


-- Count distinct rows with at least one core issue.
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE missing_trip_time
           OR nonpositive_duration
           OR pickup_outside_source_month
           OR missing_distance
           OR nonpositive_distance
           OR negative_charge
           OR missing_charge
    ) AS rows_with_core_issues,

    COUNT(*) FILTER (
        WHERE distance_over_100_miles
    ) AS distance_review_rows,

    COUNT(*) FILTER (
        WHERE duration_over_6_hours
    ) AS duration_review_rows

FROM staging.yellow_trips_quality;


-- Inspect the ten largest recorded distances.
SELECT
    source_row_number,
    pickup_datetime,
    dropoff_datetime,
    trip_distance,
    ROUND(trip_duration_minutes, 2) AS duration_minutes,
    fare_amount,
    total_amount,
    pickup_location_id,
    dropoff_location_id

FROM staging.yellow_trips_quality
ORDER BY trip_distance DESC NULLS LAST
LIMIT 10;