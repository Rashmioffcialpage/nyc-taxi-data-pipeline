with daily as (
    select coalesce(sum(trip_count), 0) as trip_count
    from {{ ref('daily_trip_summary') }}
),

trips as (
    select count(*) as trip_count
    from {{ ref('fct_yellow_trips') }}
)

select
    daily.trip_count as daily_count,
    trips.trip_count as retained_count

from daily
cross join trips

where daily.trip_count <> trips.trip_count