# NYC Taxi Data Pipeline — Local Portfolio Milestone

## Data scope

January–February 2024 NYC TLC yellow taxi records:

- 5,972,150 source records
- 5,768,183 retained trips
- 203,967 excluded under documented analysis rules
- Raw records preserved for inspection

## Implemented

- Batch ingestion with PyArrow and PostgreSQL COPY
- SHA-256 tracking and duplicate-import protection
- SQL quality flags and reconciliation checks
- Five dbt models, including daily pickup-zone summaries
- Manually triggered local Airflow orchestration
- FastAPI endpoints and React analytics dashboard
- Inclusive date filters across cards, charts, and zone rankings
- Empty-period handling and input validation
- Console logs and JSON pipeline run summaries

## Verified

- 10 Python unit tests passed
- 14 API integration tests passed locally
- Full dbt build: 5 models and 20 data tests passed
- Frontend lint and production build passed locally
- Airflow run succeeded on its first attempt
- Browser recovery after an API outage was manually checked
- Empty date-range display was checked in the browser
- GitHub Actions passed for unit tests and frontend checks
  at commit 09f3e55

## Limitations

- Runs locally; public deployment is not included.
- Airflow runs are manual; automatic scheduling is not enabled.
- API integration tests require the local database and API.
- Fixed dataset assertions cover January–February 2024.
- The last npm audit reported 10 moderate development-tool
  findings and zero production dependency findings.
- Recorded charges are not driver earnings or profit.
- This portfolio prototype does not establish production readiness.