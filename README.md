# Fishing Conditions Data Pipeline — U'Sam Fishing Bay

An automated ETL pipeline that pulls daily weather forecast data from the
Open-Meteo API, cleans it with pandas, and loads it into MySQL (with a CSV
backup). Extended with historical/marine data analysis correlating weather
conditions against real sales figures, secured credential management, and
full Docker containerization.

---

## Why this project exists

Wind, rain, and sea conditions directly affect whether it's safe or worthwhile
to go out fishing. This pipeline automates collecting that data daily so it
can eventually be analyzed alongside real sales figures — turning a routine
ETL exercise into something that could genuinely support business decisions.

---

## What this demonstrates

| Concept | How it's implemented | Why it matters |
|---|---|---|
| **ETL pattern** | Separate `fetch → clean → load` functions | Mirrors real-world data engineering structure — each stage can be tested/debugged independently |
| **Consuming a public REST API** | `requests` against Open-Meteo's Forecast, Archive, and Marine APIs (no auth required) | Core skill for pulling any external data source |
| **Transforming columnar JSON → tabular data** | Converting parallel arrays (`time[]`, `temperature[]`, etc.) into a proper pandas DataFrame | APIs rarely return data ready-to-analyze; this is where most real data work happens |
| **Idempotent database writes** | `ON DUPLICATE KEY UPDATE` on a `UNIQUE KEY (forecast_date)` | The pipeline can be safely re-run any number of times without creating duplicate rows |
| **Structured error handling** | Separate `except` blocks for API failures vs database failures | Makes real failures diagnosable instead of a generic crash |
| **Secrets management** | Credentials in `.env`, loaded via `python-dotenv`, excluded from Git via `.gitignore` | Prevents passwords from ever being committed to version control |
| **Cross-service correlation analysis** | Joining daily sales totals against weather/marine data by date | Demonstrates aggregating to a common grain before joining datasets of different granularity |
| **Containerization** | Multi-stage-friendly `Dockerfile`, `.dockerignore`, `host.docker.internal` for host DB access | Same TLS/security-project pattern applied to a data pipeline instead of a server |

---

## Architecture

```
   Open-Meteo APIs                 Docker Container              MySQL (host)
  ┌────────────────┐    HTTP    ┌──────────────────────┐  INSERT  ┌────────────────┐
  │ Forecast API     │ ────────▶ │ 1. requests.get()      │ ───────▶ │ fishing_        │
  │ Archive API       │ ◀──────── │ 2. pandas cleanup      │          │ conditions      │
  │ Marine API         │  JSON    │ 3. idempotent insert    │          └────────────────┘
  └────────────────┘             │ 4. CSV backup            │
                                 └──────────────────────┘
                                   host.docker.internal
                                   (container → host DB)
```

---

## Stack

Python, requests, pandas, MySQL, mysql-connector-python, python-dotenv,
Docker

---

## Project structure

```
usam-weather-pipeline/
├── fishing_weather_pipeline.py   # main ETL pipeline (forecast → MySQL/CSV)
├── weather_sales_analysis.py     # historical + marine data correlation analysis
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env                            # credentials (NOT committed)
├── .gitignore
└── weather_log.csv                 # CSV backup, appended each run
```

---

## How to run it

### Locally

```bash
pip install -r requirements.txt
python fishing_weather_pipeline.py
```

### In Docker

```bash
docker build -t usam-weather-pipeline .
docker run --rm --env-file .env usam-weather-pipeline
```

> **Note:** since MySQL runs on the host machine (not inside a container),
> `.env` sets `DB_HOST=host.docker.internal` instead of `localhost` — the
> special hostname Docker Desktop provides for containers to reach services
> running on the host.

---

## The pipeline (`fishing_weather_pipeline.py`)

1. **Extract** — calls Open-Meteo's Forecast API for a 7-day outlook
2. **Transform** — converts the columnar JSON response into a clean
   DataFrame, parses dates, drops incomplete rows
3. **Load (MySQL)** — inserts into `fishing_conditions`, using
   `ON DUPLICATE KEY UPDATE` so re-running the script updates existing rows
   instead of duplicating or erroring
4. **Load (CSV)** — appends the same cleaned data to `weather_log.csv` as an
   independent backup

```sql
CREATE TABLE fishing_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    forecast_date DATE NOT NULL,
    temp_max_c DECIMAL(4,1),
    temp_min_c DECIMAL(4,1),
    wind_speed_max_kmh DECIMAL(5,1),
    precipitation_mm DECIMAL(5,1),
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_forecast_date (forecast_date)
);
```

---

## The analysis (`weather_sales_analysis.py`)

Pulls **historical** weather (Archive API) and **marine** conditions (Marine
API — wave height, wave period) for the same date range as a sales CSV,
aggregates sales to one total per day, and joins all three datasets by date
to compute correlations.

```
      date  total_sales_ghs  temp_max_c  wind_speed_max_kmh  precipitation_mm
2026-08-01           1337.5        27.9                17.7               0.6
2026-08-02           1250.0        27.3                21.6               0.6
2026-08-03           1047.0        27.8                14.3               2.5
2026-08-04           1335.5        28.0                13.3               1.0
2026-08-05           1626.0        29.8                18.4               4.4
2026-08-06           1013.0        28.4                18.4               6.1

Correlation between wind speed and sales: 0.134
Correlation between precipitation and sales: -0.171
```

**Honest interpretation:** both correlations are weak, and 6 days is far too
small a sample to draw real conclusions — a single unusual day can swing a
correlation like this substantially. Correlation also doesn't imply
causation even with more data. This becomes a meaningful analysis once the
scheduled pipeline has logged weeks or months of real data.

---

## Problems hit and how they were solved

- **`ModuleNotFoundError: No module named 'requests'` in VS Code's terminal**
  — VS Code's integrated terminal was pointed at a different Python
  installation (3.14) than the one packages were installed into via Git Bash
  (3.13). Solved by running the script from Git Bash instead, where the
  installed packages were actually available.
- **`Access denied for user 'root'@'localhost'`** — the password hardcoded in
  `DB_CONFIG` didn't match the actual MySQL root password. Fixed by
  correcting it, and later solved properly by moving credentials to `.env`.
- **`FileNotFoundError` loading the sales CSV** — the CSV was in `Downloads`,
  not the project folder. Solved by copying it into the working directory
  before running the script.
- **Docker container needed to reach MySQL on the host** — `localhost` inside
  a container refers to the container itself, not the host machine. Solved
  using Docker Desktop's special `host.docker.internal` hostname in `.env`.
- **A container run showed "Inserted/updated 0 rows"** — this is expected,
  not a bug: `ON DUPLICATE KEY UPDATE` only counts a row as affected if its
  values actually changed. Running the pipeline again with unchanged forecast
  data correctly did nothing, proving the idempotency logic works as
  designed.

---

## Hardening / good-practice checklist

- [x] Idempotent database writes (`ON DUPLICATE KEY UPDATE`)
- [x] Structured error handling (API errors vs DB errors handled separately)
- [x] Credentials in `.env`, excluded from Git via `.gitignore`
- [x] Dockerized, with dependencies isolated via `requirements.txt`
- [x] `.dockerignore` keeps secrets and clutter out of the built image
- [ ] Automated daily scheduling (Windows Task Scheduler / cron)
- [ ] Larger historical dataset before drawing real conclusions from
      correlation analysis

---

## Next steps

- Schedule the pipeline to run daily via Task Scheduler, building up enough
  history for the correlation analysis to actually mean something
- Extend the sales-weather join to a full season of data
- Push the Docker image to Docker Hub or a private registry for deployment
  beyond the local machine
