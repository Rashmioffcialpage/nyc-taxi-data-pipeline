BEGIN;

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE VIEW staging.yellow_trips_quality AS
SELECT
    t.source_file,
    t.source_row_number,
    t.vendor_id,
    t.pickup_datetime,
    t.dropoff_datetime,
    t.passenger_count,
    t.trip_distance,
    t.ratecode_id,
    t.store_and_fwd_flag,
    t.pickup_location_id,
    t.dropoff_location_id,
    t.payment_type,
    t.fare_amount,
    t.extra,
    t.mta_tax,
    t.tip_amount,
    t.tolls_amount,
    t.improvement_surcharge,
    t.total_amount,
    t.congestion_surcharge,
    t.airport_fee,

    EXTRACT(
        EPOCH FROM (t.dropoff_datetime - t.pickup_datetime)
    ) / 60.0 AS trip_duration_minutes,

    (
        t.pickup_datetime IS NULL
        OR t.dropoff_datetime IS NULL
    ) AS missing_trip_time,

    COALESCE(
        t.dropoff_datetime <= t.pickup_datetime,
        FALSE
    ) AS nonpositive_duration,

    COALESCE(
        t.pickup_datetime < t.source_month
        OR t.pickup_datetime >=
            t.source_month + INTERVAL '1 month',
        FALSE
    ) AS pickup_outside_source_month,

    (t.trip_distance IS NULL) AS missing_distance,

    COALESCE(
        t.trip_distance <= 0,
        FALSE
    ) AS nonpositive_distance,

    COALESCE(
        t.fare_amount < 0 OR t.total_amount < 0,
        FALSE
    ) AS negative_charge,

    (
        t.fare_amount IS NULL
        OR t.total_amount IS NULL
    ) AS missing_charge,

    (t.passenger_count IS NULL) AS missing_passenger_count,

    COALESCE(
        t.passenger_count = 0,
        FALSE
    ) AS zero_passenger_count,

    -- Analysis review thresholds, not universal error rules.
    COALESCE(
        t.trip_distance > 100,
        FALSE
    ) AS distance_over_100_miles,

    COALESCE(
        t.dropoff_datetime - t.pickup_datetime
            > INTERVAL '6 hours',
        FALSE
    ) AS duration_over_6_hours,

    t.source_month

FROM (
    SELECT
        r.*,
        i.source_month
    FROM raw.yellow_trips AS r
    LEFT JOIN raw.ingestion_files AS i
        ON r.source_file = i.source_file
) AS t;

COMMIT;


-- Profile each source month.
SELECT
    source_month,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (
        WHERE pickup_outside_source_month
    ) AS outside_month,
    COUNT(*) FILTER (
        WHERE source_month IS NULL
    ) AS unrecognized_source_month
FROM staging.yellow_trips_quality
GROUP BY source_month
ORDER BY source_month;


-- Inspect the ten largest recorded distances.
SELECT
    source_file,
    source_row_number,
    pickup_datetime,
    dropoff_datetime,
    trip_distance,
    ROUND(trip_duration_minutes, 2) AS duration_minutes,
    fare_amount,
    total_amount
FROM staging.yellow_trips_quality
ORDER BY trip_distance DESC NULLS LAST
LIMIT 10;