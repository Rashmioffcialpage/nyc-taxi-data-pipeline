BEGIN;

DO $$
DECLARE
    source_count BIGINT;
    retained_count BIGINT;
    excluded_count BIGINT;
    logged_count BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO source_count
    FROM raw.yellow_trips
    WHERE source_file = 'yellow_tripdata_2024-01.parquet';

    IF source_count = 0 THEN
        RAISE EXCEPTION 'FAIL: January source data is empty';
    END IF;

    SELECT row_count
    INTO logged_count
    FROM raw.ingestion_files
    WHERE source_file = 'yellow_tripdata_2024-01.parquet';

    IF logged_count IS DISTINCT FROM source_count THEN
        RAISE EXCEPTION
            'FAIL: Import log (%) differs from raw row count (%)',
            logged_count, source_count;
    END IF;

    RAISE NOTICE 'PASS: Import log matches raw data';

    SELECT COUNT(*)
    INTO retained_count
    FROM analytics.yellow_trips;

    SELECT COUNT(*)
    INTO excluded_count
    FROM staging.yellow_trips_excluded;

    IF retained_count = 0 THEN
        RAISE EXCEPTION 'FAIL: Analytical subset is empty';
    END IF;

    IF source_count <> retained_count + excluded_count THEN
        RAISE EXCEPTION
            'FAIL: Retained and excluded counts do not reconcile';
    END IF;

    RAISE NOTICE 'PASS: Row counts reconcile';

    IF EXISTS (
        SELECT 1
        FROM analytics.yellow_trips AS a
        JOIN staging.yellow_trips_excluded AS e
          ON a.source_file = e.source_file
         AND a.source_row_number = e.source_row_number
    ) THEN
        RAISE EXCEPTION 'FAIL: Retained and excluded sets overlap';
    END IF;

    RAISE NOTICE 'PASS: Retained and excluded sets are disjoint';

    IF EXISTS (
        SELECT 1
        FROM analytics.yellow_trips
        GROUP BY source_file, source_row_number
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'FAIL: Duplicate analytical source-row keys';
    END IF;

    RAISE NOTICE 'PASS: Analytical source-row keys are unique';

    IF EXISTS (
        SELECT 1
        FROM analytics.yellow_trips
        WHERE pickup_datetime IS NULL
           OR dropoff_datetime IS NULL
           OR pickup_datetime < TIMESTAMP '2024-01-01'
           OR pickup_datetime >= TIMESTAMP '2024-02-01'
           OR trip_duration_minutes IS NULL
           OR trip_duration_minutes <= 0
           OR trip_duration_minutes > 360
           OR trip_distance IS NULL
           OR trip_distance <= 0
           OR trip_distance > 100
           OR fare_amount IS NULL
           OR fare_amount < 0
           OR total_amount IS NULL
           OR total_amount < 0
    ) THEN
        RAISE EXCEPTION
            'FAIL: Analytical rows violate documented filter rules';
    END IF;

    RAISE NOTICE 'PASS: Analytical rows satisfy filter rules';

    IF EXISTS (
        SELECT 1
        FROM analytics.yellow_trips AS a
        LEFT JOIN raw.taxi_zones AS p
            ON a.pickup_location_id = p.location_id
        LEFT JOIN raw.taxi_zones AS d
            ON a.dropoff_location_id = d.location_id
        WHERE p.location_id IS NULL
           OR d.location_id IS NULL
    ) THEN
        RAISE EXCEPTION 'FAIL: Analytical location IDs lack lookup rows';
    END IF;

    RAISE NOTICE 'PASS: Location IDs match the zone lookup';
    RAISE NOTICE 'All January data-quality checks passed';
END;
$$;

COMMIT;