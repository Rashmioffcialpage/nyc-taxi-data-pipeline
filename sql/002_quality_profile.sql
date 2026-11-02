-- Profile January 2024's source file without modifying raw data.
SELECT
    COUNT(*) AS total_rows,

    COUNT(*) FILTER (
        WHERE pickup_datetime IS NULL
    ) AS missing_pickup_time,

    COUNT(*) FILTER (
        WHERE dropoff_datetime IS NULL
    ) AS missing_dropoff_time,

    COUNT(*) FILTER (
        WHERE dropoff_datetime <= pickup_datetime
    ) AS nonpositive_duration,

    COUNT(*) FILTER (
        WHERE pickup_datetime < TIMESTAMP '2024-01-01'
           OR pickup_datetime >= TIMESTAMP '2024-02-01'
    ) AS pickup_outside_january,

    COUNT(*) FILTER (
        WHERE trip_distance IS NULL
    ) AS missing_distance,

    COUNT(*) FILTER (
        WHERE trip_distance <= 0
    ) AS nonpositive_distance,

    COUNT(*) FILTER (
        WHERE fare_amount < 0
    ) AS negative_fare,

    COUNT(*) FILTER (
        WHERE total_amount IS NULL
    ) AS missing_total_amount,

    COUNT(*) FILTER (
        WHERE total_amount < 0
    ) AS negative_total_amount,

    COUNT(*) FILTER (
        WHERE passenger_count IS NULL
    ) AS missing_passenger_count,

    COUNT(*) FILTER (
        WHERE passenger_count = 0
    ) AS zero_passenger_count

FROM raw.yellow_trips
WHERE source_file = 'yellow_tripdata_2024-01.parquet';


-- Check whether location IDs exist in the lookup table.
SELECT
    COUNT(*) FILTER (
        WHERE t.pickup_location_id IS NULL
    ) AS missing_pickup_location,

    COUNT(*) FILTER (
        WHERE t.pickup_location_id IS NOT NULL
          AND pickup.location_id IS NULL
    ) AS unmatched_pickup_location,

    COUNT(*) FILTER (
        WHERE t.dropoff_location_id IS NULL
    ) AS missing_dropoff_location,

    COUNT(*) FILTER (
        WHERE t.dropoff_location_id IS NOT NULL
          AND dropoff.location_id IS NULL
    ) AS unmatched_dropoff_location

FROM raw.yellow_trips AS t
LEFT JOIN raw.taxi_zones AS pickup
    ON t.pickup_location_id = pickup.location_id
LEFT JOIN raw.taxi_zones AS dropoff
    ON t.dropoff_location_id = dropoff.location_id
WHERE t.source_file = 'yellow_tripdata_2024-01.parquet';


-- Inspect the recorded time and numeric ranges.
SELECT
    MIN(pickup_datetime) AS earliest_pickup,
    MAX(pickup_datetime) AS latest_pickup,
    MIN(trip_distance) AS minimum_distance,
    MAX(trip_distance) AS maximum_distance,
    MIN(total_amount) AS minimum_total_amount,
    MAX(total_amount) AS maximum_total_amount
FROM raw.yellow_trips
WHERE source_file = 'yellow_tripdata_2024-01.parquet';