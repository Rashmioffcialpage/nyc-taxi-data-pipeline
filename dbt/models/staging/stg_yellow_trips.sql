{{ config(materialized='view') }}

select
    trips.*,
    imports.source_month,

    extract(
        epoch from (
            trips.dropoff_datetime - trips.pickup_datetime
        )
    ) / 60.0 as trip_duration_minutes

from {{ source('taxi_raw', 'yellow_trips') }} as trips

left join {{ source('taxi_raw', 'ingestion_files') }} as imports
    on trips.source_file = imports.source_file
