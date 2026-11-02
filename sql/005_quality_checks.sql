BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM raw.yellow_trips) THEN
        RAISE EXCEPTION 'FAIL: Raw trip data is empty';
    END IF;

    -- Every file must have an import log with the correct count.
    IF EXISTS (
        WITH actual AS (
            SELECT source_file, COUNT(*) AS row_count
            FROM raw.yellow_trips
            GROUP BY source_file
        )
        SELECT 1
        FROM actual AS a
        FULL OUTER JOIN raw.ingestion_files AS i
            ON a.source_file = i.source_file
        WHERE a.source_file IS NULL
           OR i.source_file IS NULL
           OR a.row_count IS DISTINCT FROM i.row_count
    ) THEN
        RAISE EXCEPTION
            'FAIL: Import logs and raw file counts do not match';
    END IF;

    RAISE NOTICE 'PASS: Import logs match every raw file';

    IF EXISTS (
        SELECT 1
        FROM staging.yellow_trips_quality
        WHERE source_month IS NULL
    ) THEN
        RAISE EXCEPTION 'FAIL: Unrecognized source month';
    END IF;

    RAISE NOTICE 'PASS: Every source month is recognized';

    -- Reconcile counts separately for each source file.
    IF EXISTS (
        WITH source_counts AS (
            SELECT source_file, COUNT(*) AS n
            FROM raw.yellow_trips
            GROUP BY source_file
        ),
        retained_counts AS (
            SELECT source_file, COUNT(*) AS n
            FROM analytics.yellow_trips
            GROUP BY source_file
        ),
        excluded_counts AS (
            SELECT source_file, COUNT(*) AS n
            FROM staging.yellow_trips_excluded
            GROUP BY source_file
        )
        SELECT 1
        FROM source_counts AS s
        LEFT JOIN retained_counts AS r USING (source_file)
        LEFT JOIN excluded_counts AS e USING (source_file)
        WHERE s.n <> COALESCE(r.n, 0) + COALESCE(e.n, 0)
    ) THEN
        RAISE EXCEPTION 'FAIL: Per-file counts do not reconcile';
    END IF;

    RAISE NOTICE 'PASS: Per-file counts reconcile';

    IF NOT EXISTS (SELECT 1 FROM analytics.yellow_trips) THEN
        RAISE EXCEPTION 'FAIL: Analytical subset is empty';
    END IF;

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

    -- Check month membership using the source row's derived month.
    IF EXISTS (
        SELECT 1
        FROM analytics.yellow_trips AS a
        JOIN staging.yellow_trips_quality AS q
          ON a.source_file = q.source_file
         AND a.source_row_number = q.source_row_number
        WHERE q.source_month IS NULL
           OR a.pickup_datetime IS NULL
           OR a.dropoff_datetime IS NULL
           OR a.pickup_datetime < q.source_month
           OR a.pickup_datetime >=
                q.source_month + INTERVAL '1 month'
           OR a.trip_duration_minutes IS NULL
           OR a.trip_duration_minutes <= 0
           OR a.trip_duration_minutes > 360
           OR a.trip_distance IS NULL
           OR a.trip_distance <= 0
           OR a.trip_distance > 100
           OR a.fare_amount IS NULL
           OR a.fare_amount < 0
           OR a.total_amount IS NULL
           OR a.total_amount < 0
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
        RAISE EXCEPTION 'FAIL: Location IDs lack lookup rows';
    END IF;

    RAISE NOTICE 'PASS: Location IDs match the zone lookup';
    RAISE NOTICE 'All multi-month data-quality checks passed';
END;
$$;

COMMIT;