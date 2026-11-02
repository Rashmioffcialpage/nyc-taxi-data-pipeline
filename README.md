# NYC Taxi Data Pipeline

A local data engineering project using Python, PostgreSQL, and SQL
to ingest, inspect, and summarize NYC yellow taxi trip records.

## Current status

The January 2024 pipeline is implemented and verified.

- Batch ingestion using PyArrow and PostgreSQL COPY
- SHA-256 file tracking and duplicate-import protection
- Raw records preserved separately from analytical views
- Data-quality flags and six automated quality checks
- Daily and pickup-zone summaries with count reconciliation
- One-command pipeline runner

Multi-month processing, backfills, dbt, scheduling, and visualization
are planned, not yet implemented.

## Verified results

| Metric | Result |
| --- | ---: |
| Source trips | 2,964,624 |
| Taxi-zone lookup rows | 265 |
| Retained analytical trips | 2,868,179 |
| Excluded trips | 96,445 |
| Excluded share | 3.25% |
| Average retained distance | 3.29 miles |
| Average retained duration | 14.97 minutes |
| Average retained recorded total charge | $27.34 |

A local rerun completed in 22 seconds. This skipped the existing trip
import and rebuilt and checked the views; it is not a fresh-load benchmark.

## Data flow

Official TLC files → raw PostgreSQL tables → quality flags →
analytical trip subset → daily and pickup-zone summaries.

The source filename and row number identify each imported trip.
An unchanged previously loaded file is skipped. A changed file with
the same name is rejected for investigation.

## Analytical scope

The current analytical subset excludes trips with:

- Missing pickup or drop-off times
- Nonpositive duration
- Pickup outside January 2024
- Missing or nonpositive distance
- Missing fare or total charge
- Negative fare or total charge
- Distance above 100 miles
- Duration above six hours

The distance and duration thresholds define this project's analysis
scope; they are not universal definitions of invalid trips.
Negative charges may represent adjustments.

Missing or zero passenger counts remain in the analytical subset.
Raw and excluded records remain available for inspection.

Recorded total charges are not profit or driver earnings.
Results describe the retained sample, not all NYC transportation activity.

## Setup

Requirements: Python with a working virtual environment, Docker Desktop,
and Docker Compose.

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
docker compose up -d
```

PostgreSQL is exposed locally on port 5434.
The credentials in compose.yaml are for local development only.

## Download the source files

```bash
mkdir -p data/raw

curl -L --fail --retry 3 \
  "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet" \
  --output data/raw/yellow_tripdata_2024-01.parquet

curl -L --fail --retry 3 \
  "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv" \
  --output data/raw/taxi_zone_lookup.csv
```

Raw datasets are excluded from Git.

## Run the pipeline

With Docker Desktop and the database running:

```bash
python -m ingestion.run_pipeline
```

The runner stops if a command fails. Steps commit separately;
an earlier successful import remains if a later step fails.

The Python importers default to the local database in compose.yaml.
The current runner executes SQL against that Docker database.

## Verification

The pipeline checks:

- Import-log and raw-row counts agree
- Retained and excluded counts reconcile
- Retained and excluded sets do not overlap
- Analytical source-row keys are unique
- Retained rows satisfy the documented filters
- Location IDs match the zone lookup

Daily and pickup-zone summaries also reconcile with the retained count.

These checks enforce structural and filtering rules. They do not prove
that every retained source record is accurate.

## Project structure

- ingestion/: inspection, loading, and pipeline runner
- sql/: schemas, quality flags, checks, and analytical views
- data/raw/: locally downloaded source files
- docs/: project documentation

## Source

NYC Taxi and Limousine Commission:
https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

Datasets: January 2024 yellow taxi trips and the taxi-zone lookup.