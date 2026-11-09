{{ config(materialized='table') }}

select
    trips.pickup_location_id,
    zones.borough as pickup_borough,
    zones.zone as pickup_zone,

    count(*) as trip_count,

    round(
        avg(trips.trip_distance::numeric), 2
    ) as average_distance_miles,

    round(
        avg(trips.trip_duration_minutes), 2
    ) as average_duration_minutes,

    round(
        sum(trips.total_amount::numeric), 2
    ) as recorded_total_charges_usd,

    round(
        avg(trips.total_amount::numeric), 2
    ) as average_recorded_total_usd

from {{ ref('fct_yellow_trips') }} as trips

left join {{ source('taxi_raw', 'taxi_zones') }} as zones
    on trips.pickup_location_id = zones.location_id

group by
    trips.pickup_location_id,
    zones.borough,
    zones.zone