{{ config(materialized='table') }}

select
    pickup_datetime::date as pickup_date,

    count(*) as trip_count,

    round(
        sum(trip_distance::numeric), 2
    ) as total_distance_miles,

    round(
        avg(trip_distance::numeric), 2
    ) as average_distance_miles,

    round(
        avg(trip_duration_minutes), 2
    ) as average_duration_minutes,

    round(
        sum(total_amount::numeric), 2
    ) as recorded_total_charges_usd,

    round(
        avg(total_amount::numeric), 2
    ) as average_recorded_total_usd

from {{ ref('fct_yellow_trips') }}

group by pickup_datetime::date