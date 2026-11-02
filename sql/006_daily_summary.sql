BEGIN;

CREATE OR REPLACE VIEW analytics.daily_trip_summary AS
SELECT
    pickup_date,

    COUNT(*) AS trip_count,

    ROUND(
        SUM(trip_distance::numeric), 2
    ) AS total_distance_miles,

    ROUND(
        AVG(trip_distance::numeric), 2
    ) AS average_distance_miles,

    ROUND(
        AVG(trip_duration_minutes), 2
    ) AS average_duration_minutes,

    ROUND(
        SUM(total_amount::numeric), 2
    ) AS recorded_total_charges_usd,

    ROUND(
        AVG(total_amount::numeric), 2
    ) AS average_recorded_total_usd

FROM analytics.yellow_trips
GROUP BY pickup_date;

-- Verify that aggregation preserves the retained trip count.
DO $$
DECLARE
    daily_count BIGINT;
    retained_count BIGINT;
BEGIN
    SELECT SUM(trip_count)
    INTO daily_count
    FROM analytics.daily_trip_summary;

    SELECT COUNT(*)
    INTO retained_count
    FROM analytics.yellow_trips;

    IF daily_count IS DISTINCT FROM retained_count THEN
        RAISE EXCEPTION
            'FAIL: Daily trip count (%) differs from retained count (%)',
            daily_count, retained_count;
    END IF;

    RAISE NOTICE 'PASS: Daily summary reconciles with retained trips';
END;
$$;

COMMIT;

-- Preview the first seven days.
SELECT *
FROM analytics.daily_trip_summary
ORDER BY pickup_date
LIMIT 7;

-- Find the five busiest days in the retained subset.
SELECT
    pickup_date,
    trip_count,
    recorded_total_charges_usd
FROM analytics.daily_trip_summary
ORDER BY trip_count DESC, pickup_date
LIMIT 5;