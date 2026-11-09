WITH zone_counts AS (
    SELECT
        pickup_date,
        SUM(trip_count) AS trip_count
    FROM {{ ref('daily_pickup_zone_summary') }}
    GROUP BY pickup_date
),

daily_counts AS (
    SELECT
        pickup_date,
        trip_count
    FROM {{ ref('daily_trip_summary') }}
)

SELECT
    COALESCE(z.pickup_date, d.pickup_date) AS pickup_date,
    z.trip_count AS zone_trip_count,
    d.trip_count AS daily_trip_count

FROM zone_counts AS z

FULL OUTER JOIN daily_counts AS d
    ON z.pickup_date = d.pickup_date

WHERE
    z.pickup_date IS NULL
    OR d.pickup_date IS NULL
    OR z.trip_count IS DISTINCT FROM d.trip_count