with zones as (
    select coalesce(sum(trip_count), 0) as trip_count
    from {{ ref('pickup_zone_summary') }}
),

trips as (
    select count(*) as trip_count
    from {{ ref('fct_yellow_trips') }}
)

select
    zones.trip_count as zone_count,
    trips.trip_count as retained_count

from zones
cross join trips

where zones.trip_count <> trips.trip_count