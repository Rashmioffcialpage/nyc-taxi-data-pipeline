{{ config(materialized='table') }}

SELECT
    trips.pickup_datetime::date AS pickup_date,
    trips.pickup_location_id,
    zones.borough AS pickup_borough,
    zones.zone AS pickup_zone,

    COUNT(*) AS trip_count,

    SUM(trips.trip_distance::numeric) AS total_distance_miles,

    SUM(
        EXTRACT(
            EPOCH FROM (
                trips.dropoff_datetime - trips.pickup_datetime
            )
        )::numeric / 60.0
    ) AS total_duration_minutes,

    SUM(
        trips.total_amount::numeric
    ) AS recorded_total_charges_usd

FROM {{ ref('fct_yellow_trips') }} AS trips

LEFT JOIN {{ source('taxi_raw', 'taxi_zones') }} AS zones
    ON trips.pickup_location_id = zones.location_id

GROUP BY
    trips.pickup_datetime::date,
    trips.pickup_location_id,
    zones.borough,
    zones.zone