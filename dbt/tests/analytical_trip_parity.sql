-- A dbt data test fails when this query returns rows.
-- Compare membership using source file and row number.

with dbt_only as (
    select source_file, source_row_number
    from {{ ref('fct_yellow_trips') }}

    except

    select source_file, source_row_number
    from analytics.yellow_trips
),

legacy_only as (
    select source_file, source_row_number
    from analytics.yellow_trips

    except

    select source_file, source_row_number
    from {{ ref('fct_yellow_trips') }}
)

select 'dbt_only' as difference, *
from dbt_only

union all

select 'legacy_only' as difference, *
from legacy_only