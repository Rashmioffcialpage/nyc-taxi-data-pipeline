BEGIN;

CREATE OR REPLACE VIEW analytics.pickup_zone_summary AS
SELECT
    pickup_location_id,
    pickup_borough,
    pickup_zone,

    COUNT(*) AS trip_count,

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

GROUP BY
    pickup_location_id,
    pickup_borough,
    pickup_zone;


-- Verify that every retained trip belongs to one summary group.
DO $$
DECLARE
    zone_count BIGINT;
    retained_count BIGINT;
BEGIN
    SELECT SUM(trip_count)
    INTO zone_count
    FROM analytics.pickup_zone_summary;

    SELECT COUNT(*)
    INTO retained_count
    FROM analytics.yellow_trips;

    IF zone_count IS DISTINCT FROM retained_count THEN
        RAISE EXCEPTION
            'FAIL: Zone summary count (%) differs from retained count (%)',
            zone_count, retained_count;
    END IF;

    RAISE NOTICE 'PASS: Pickup-zone summary reconciles with retained trips';
END;
$$;

COMMIT;


-- Ten busiest pickup zones in the retained subset.
SELECT
    pickup_location_id,
    pickup_borough,
    pickup_zone,
    trip_count,
    average_distance_miles,
    average_recorded_total_usd

FROM analytics.pickup_zone_summary
ORDER BY trip_count DESC, pickup_location_id
LIMIT 10;


-- Trip counts by pickup borough.
SELECT
    pickup_borough,
    SUM(trip_count) AS trip_count

FROM analytics.pickup_zone_summary
GROUP BY pickup_borough
ORDER BY trip_count DESC, pickup_borough;