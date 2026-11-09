import { useEffect, useState } from 'react'
import './App.css'

type Summary = {
  first_pickup_date: string | null
  last_pickup_date: string | null
  days_with_trips: number
  trip_count: number
  average_distance_miles: number | null
  recorded_total_charges_usd: number | null
  average_recorded_total_usd: number | null
  scope: string
  charges_note: string
}

type DailyTrip = {
  pickup_date: string
  trip_count: number
}

type Zone = {
  pickup_location_id: number
  pickup_borough: string | null
  pickup_zone: string | null
  trip_count: number
  average_distance_miles: number | null
  average_recorded_total_usd: number | null
}

type Dashboard = {
  summary: Summary
  daily: DailyTrip[]
  zones: Zone[]
}

const API = 'http://127.0.0.1:8003'
const number = new Intl.NumberFormat('en-US')
const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

function formatDate(value: string | null) {
  if (!value) return '—'

  return new Date(`${value}T00:00:00`).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatMoney(value: number | null) {
  return value === null ? '—' : money.format(value)
}

async function getJson<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    signal,
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`The API returned HTTP ${response.status}.`)
  }

  return response.json() as Promise<T>
}

function DailyChart({ rows }: { rows: DailyTrip[] }) {
  if (rows.length === 0) {
    return <p>No daily trip records are available.</p>
  }

  const width = 900
  const height = 280
  const left = 65
  const right = 20
  const top = 20
  const bottom = 45
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const maximum = Math.max(1, ...rows.map((row) => row.trip_count))
  const ceiling = Math.ceil(maximum / 25000) * 25000

  const x = (index: number) =>
    left + (index / Math.max(1, rows.length - 1)) * plotWidth

  const y = (count: number) =>
    top + plotHeight - (count / ceiling) * plotHeight

  const points = rows
    .map((row, index) => `${x(index)},${y(row.trip_count)}`)
    .join(' ')

  const labelIndexes = Array.from(
    new Set([0, Math.floor((rows.length - 1) / 2), rows.length - 1]),
  )

  return (
    <div className="chart-scroll">
      <svg
        className="daily-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby="daily-chart-title daily-chart-description"
      >
        <title id="daily-chart-title">Daily retained taxi trips</title>
        <desc id="daily-chart-description">
          Trip counts from {rows[0].pickup_date} through{' '}
          {rows[rows.length - 1].pickup_date}. Exact values are available
          in the daily data table below.
        </desc>

        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const count = ceiling * fraction

          return (
            <g key={fraction}>
              <line
                x1={left}
                x2={width - right}
                y1={y(count)}
                y2={y(count)}
                className="grid-line"
              />
              <text
                x={left - 10}
                y={y(count) + 4}
                textAnchor="end"
                className="axis-label"
              >
                {number.format(count)}
              </text>
            </g>
          )
        })}

        <polyline
          points={points}
          fill="none"
          stroke="#2563eb"
          strokeWidth="3"
          strokeLinejoin="round"
        />

        {rows.map((row, index) => (
          <circle
            key={row.pickup_date}
            cx={x(index)}
            cy={y(row.trip_count)}
            r="3"
            fill="#2563eb"
          >
            <title>
              {formatDate(row.pickup_date)}: {number.format(row.trip_count)} trips
            </title>
          </circle>
        ))}

        {labelIndexes.map((index) => (
          <text
            key={index}
            x={x(index)}
            y={height - 12}
            textAnchor={
              index === 0
                ? 'start'
                : index === rows.length - 1
                  ? 'end'
                  : 'middle'
            }
            className="axis-label"
          >
            {formatDate(rows[index].pickup_date)}
          </text>
        ))}
      </svg>
    </div>
  )
}

function App() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [request, setRequest] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 20000)
    let active = true

    async function load() {
      try {
        const [summary, daily, zones] = await Promise.all([
          getJson<Summary>('/api/summary', controller.signal),
          getJson<{ results: DailyTrip[] }>(
            '/api/trips/daily',
            controller.signal,
          ),
          getJson<{ results: Zone[] }>(
            '/api/zones/top?limit=10',
            controller.signal,
          ),
        ])

        if (active) {
          setData({
            summary,
            daily: daily.results,
            zones: zones.results,
          })
        }
      } catch (caught) {
        if (active) {
          const message =
            caught instanceof Error ? caught.message : 'Unknown error.'

          setError(
            `Could not load the dashboard. Check that the API on port 8003 ` +
              `and PostgreSQL are running, then retry. ${message}`,
          )
        }
      } finally {
        window.clearTimeout(timeout)
        if (active) setLoading(false)
      }
    }

    void load()

    return () => {
      active = false
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [request])

  function reload() {
    setError('')
    setData(null)
    setLoading(true)
    setRequest((previous) => previous + 1)
  }

  const busiest = data?.daily.reduce<DailyTrip | null>(
    (best, row) => (!best || row.trip_count > best.trip_count ? row : best),
    null,
  )

  return (
    <main className="dashboard">
      <header className="page-header">
        <div>
          <p className="eyebrow">NYC TAXI · DATA ENGINEERING</p>
          <h1>From trip records to insights.</h1>
          <p className="subtitle">
            Explore retained yellow taxi trips through a PostgreSQL,
            Python, dbt, and Airflow pipeline.
          </p>
        </div>

        <a
          className="github-link"
          href="https://github.com/Rashmioffcialpage/nyc-taxi-data-pipeline"
          target="_blank"
          rel="noreferrer"
        >
          View GitHub ↗
        </a>
      </header>

      <div className="toolbar">
        <p>
          {data
            ? `${formatDate(data.summary.first_pickup_date)} – ${formatDate(
                data.summary.last_pickup_date,
              )}`
            : 'NYC yellow taxi analytics'}
        </p>

        <button type="button" onClick={reload} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh data'}
        </button>
      </div>

      {loading && <p role="status">Loading dashboard data…</p>}

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          <section className="metrics" aria-label="Trip summary">
            <article className="metric">
              <p>Retained trips</p>
              <h2>{number.format(data.summary.trip_count)}</h2>
              <span>{data.summary.days_with_trips} days with trips</span>
            </article>

            <article className="metric">
              <p>Average distance</p>
              <h2>
                {data.summary.average_distance_miles?.toFixed(2) ?? '—'}
                <small> miles</small>
              </h2>
              <span>Across retained trips</span>
            </article>

            <article className="metric">
              <p>Recorded total charges</p>
              <h2>{formatMoney(data.summary.recorded_total_charges_usd)}</h2>
              <span>USD · source-recorded amounts</span>
            </article>

            <article className="metric">
              <p>Average recorded charge</p>
              <h2>{formatMoney(data.summary.average_recorded_total_usd)}</h2>
              <span>Per retained trip</span>
            </article>
          </section>

          <aside className="scope-note">
            {data.summary.scope} {data.summary.charges_note}
            {' '}Results describe this dataset and analysis scope.
          </aside>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">TRIP VOLUME</p>
                <h2>Daily retained trips</h2>
              </div>
              {busiest && (
                <p className="highlight">
                  Busiest day: <strong>{formatDate(busiest.pickup_date)}</strong>
                  <br />
                  {number.format(busiest.trip_count)} trips
                </p>
              )}
            </div>

            <DailyChart rows={data.daily} />

            <details className="daily-details">
              <summary>View exact daily counts</summary>
              <div className="table-scroll">
                <table>
                  <caption>Retained trips by pickup date</caption>
                  <thead>
                    <tr>
                      <th scope="col">Pickup date</th>
                      <th scope="col" className="numeric">Trips</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.daily.map((row) => (
                      <tr key={row.pickup_date}>
                        <td>{formatDate(row.pickup_date)}</td>
                        <td className="numeric">
                          {number.format(row.trip_count)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">PICKUP LOCATIONS</p>
                <h2>Ten busiest pickup zones</h2>
              </div>
              <p className="muted">Ranked by retained trip count</p>
            </div>

            {data.zones.length === 0 ? (
              <p>No pickup-zone records are available.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <caption>Top pickup zones across the full loaded period</caption>
                  <thead>
                    <tr>
                      <th scope="col">Zone</th>
                      <th scope="col">Borough</th>
                      <th scope="col" className="numeric">Trips</th>
                      <th scope="col" className="numeric">Avg. miles</th>
                      <th scope="col" className="numeric">Avg. charge</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.zones.map((zone) => (
                      <tr key={zone.pickup_location_id}>
                        <th scope="row">
                          {zone.pickup_zone ?? 'Unknown zone'}
                        </th>
                        <td>{zone.pickup_borough ?? 'Unknown'}</td>
                        <td className="numeric">
                          {number.format(zone.trip_count)}
                        </td>
                        <td className="numeric">
                          {zone.average_distance_miles?.toFixed(2) ?? '—'}
                        </td>
                        <td className="numeric">
                          {formatMoney(zone.average_recorded_total_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <footer>
        Source: NYC TLC yellow taxi records. Dashboard reads dbt summary
        tables; refresh retrieves their currently stored results.
      </footer>
    </main>
  )
}

export default App