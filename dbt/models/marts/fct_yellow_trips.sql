{{ config(materialized='view') }}

select *
from {{ ref('stg_yellow_trips') }}

where source_month is not null
  and pickup_datetime is not null
  and dropoff_datetime is not null

  and pickup_datetime >= source_month
  and pickup_datetime < source_month + interval '1 month'

  and trip_duration_minutes > 0
  and trip_duration_minutes <= 360

  and trip_distance > 0
  and trip_distance <= 100

  and fare_amount >= 0
  and total_amount >= 0