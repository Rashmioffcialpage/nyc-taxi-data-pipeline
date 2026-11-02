BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

-- Keep excluded records available for inspection.
CREATE OR REPLACE VIEW staging.yellow_trips_excluded AS
SELECT *
FROM staging.yellow_trips_quality
WHERE missing_trip_time
   OR nonpositive_duration
   OR pickup_outside_source_month
   OR missing_distance
   OR nonpositive_distance
   OR negative_charge
   OR missing_charge
   OR distance_over_100_miles
   OR duration_over_6_hours;


-- January 2024 analytical subset.
CREATE OR REPLACE VIEW analytics.yellow_trips AS
SELECT
    q.source_file,
    q.source_row_number,
    q.vendor_id,
    q.pickup_datetime,
    q.dropoff_datetime,
    q.pickup_datetime::date AS pickup_date,
    EXTRACT(HOUR FROM q.pickup_datetime)::integer AS pickup_hour,
    q.trip_duration_minutes,
    q.passenger_count,
    q.trip_distance,
    q.ratecode_id,
    q.payment_type,
    q.pickup_location_id,
    pickup.borough AS pickup_borough,
    pickup.zone AS pickup_zone,
    q.dropoff_location_id,
    dropoff.borough AS dropoff_borough,
    dropoff.zone AS dropoff_zone,
    q.fare_amount,
    q.tip_amount,
    q.tolls_amount,
    q.total_amount,
    q.missing_passenger_count,
    q.zero_passenger_count

FROM staging.yellow_trips_quality AS q

LEFT JOIN raw.taxi_zones AS pickup
    ON q.pickup_location_id = pickup.location_id

LEFT JOIN raw.taxi_zones AS dropoff
    ON q.dropoff_location_id = dropoff.location_id

WHERE NOT (
       q.missing_trip_time
    OR q.nonpositive_duration
    OR q.pickup_outside_source_month
    OR q.missing_distance
    OR q.nonpositive_distance
    OR q.negative_charge
    OR q.missing_charge
    OR q.distance_over_100_miles
    OR q.duration_over_6_hours
);

COMMIT;


-- Reconcile retained and excluded records.
WITH counts AS (
    SELECT
        (
            SELECT COUNT(*)
            FROM staging.yellow_trips_quality
        ) AS source_rows,
        (
            SELECT COUNT(*)
            FROM analytics.yellow_trips
        ) AS retained_rows,
        (
            SELECT COUNT(*)
            FROM staging.yellow_trips_excluded
        ) AS excluded_rows
)
SELECT
    *,
    source_rows = retained_rows + excluded_rows
        AS row_counts_reconcile,
    ROUND(
        100.0 * excluded_rows / NULLIF(source_rows, 0),
        2
    ) AS excluded_pct
FROM counts;


-- Summarize the retained subset.
SELECT
    COUNT(*) AS retained_trips,
    MIN(pickup_date) AS first_pickup_date,
    MAX(pickup_date) AS last_pickup_date,
    ROUND(AVG(trip_distance)::numeric, 2)
        AS average_distance_miles,
    ROUND(AVG(trip_duration_minutes), 2)
        AS average_duration_minutes,
    ROUND(AVG(total_amount)::numeric, 2)
        AS average_recorded_total_usd
FROM analytics.yellow_trips;