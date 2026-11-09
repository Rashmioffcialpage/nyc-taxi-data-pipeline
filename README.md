# NYC Taxi Data Pipeline

A local data engineering project using Python, PostgreSQL, and SQL
to ingest, inspect, and summarize NYC yellow taxi trip records.

## Current status

The local pipeline supports inclusive month ranges and has been
verified with January and February 2024 yellow taxi records.

Implemented:

- Batch ingestion using PyArrow and PostgreSQL COPY
- SHA-256 file tracking and duplicate-import protection
- Source-month metadata stored once per imported file
- Raw records preserved separately from analytical views
- Seven database quality checks
- Daily and pickup-zone summaries with count reconciliation
- Timestamped console logs and JSON run summaries
- Ten passing Python unit tests
- GitHub Actions workflow for unit tests and syntax checks

dbt transformations, scheduled orchestration, and dashboard
visualization remain planned.

## Verified results

| Metric | January–February 2024 |
| --- | ---: |
| Source trips | 5,972,150 |
| Taxi-zone lookup rows | 265 |
| Retained analytical trips | 5,768,183 |
| Excluded trips | 203,967 |
| Excluded share | 3.42% |
| Average retained distance | 3.26 miles |
| Average retained duration | 15.17 minutes |
| Average retained recorded total charge | $27.28 |

After replacing per-row filename parsing with source-file metadata,
observed pipeline rerun time decreased from 1,567.8 seconds to
64.0 seconds. A subsequent logged rerun completed in 58.9 seconds.

These runs skipped existing imports. They are local observations,
not fresh-load benchmarks; cache and system conditions affect timing.

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
- Pickup outside the month identified by its source file
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

Datasets: January 2024 yellow taxi trips and the taxi-zone lookup## Airflow orchestration

The `nyc_taxi_pipeline` DAG runs the logged Python pipeline,
SQL quality checks, and dbt build for January–February 2024.

- Manually triggered through the local Airflow interface.
- First verified DAG run succeeded in 1 minute 24 seconds.
- Task succeeded on its first attempt.
- Existing imports were verified and skipped without reloading.
- Airflow displays pipeline output in the task logs.
- Two retries are configured with a one-minute delay.

The pipeline processes 5,972,150 source records, retaining
5,768,183 trips and excluding 203,967 under documented analysis rules.

Airflow currently runs locally in standalone mode.
Automatic scheduling is not enabled.
Local environments, Airflow state, and connection settings
are excluded from Git.## Analytics dashboard

The FastAPI and React dashboard reads the dbt daily and pickup-zone
summary tables.

Features:
- Retained trip counts and recorded-charge summaries
- Daily trip chart with an exact-count table
- Ten busiest pickup zones
- Loading, error, and retry states

Recorded charges are not driver earnings or profit.
Dashboard refresh reads the stored summaries; it does not run the pipeline.

### Run locally

Start PostgreSQL:

```bash
docker compose up -d db
```

With the pipeline and dbt models already built, start the API:

```bash
.venv/bin/python -m uvicorn backend.main:app --reload --port 8003
```

In another terminal, start the frontend:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev -- --port 5173 --strictPort
```

Open <http://localhost:5173/>.

### Dashboard verification

With PostgreSQL and the API running:

```bash
.venv/bin/python -m unittest discover -s integration_tests -v
```

Seven API integration tests verify health, known January–February
2024 results, daily reconciliation, weighted averages, zone ordering,
and limit validation. Fixed dataset expectations must be updated
when additional months are loaded.

Frontend checks:

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

Browser error recovery was manually checked by stopping the API,
refreshing dashboard data, restarting the API, and retrying.

The last dependency audit reported ten moderate development-tool
findings and zero production dependency findings..