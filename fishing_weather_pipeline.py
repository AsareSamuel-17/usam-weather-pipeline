import os

import requests
import pandas as pd
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------- CONFIG ----------
LATITUDE = 5.55     # Accra/Tema coastline — adjust to your exact location
LONGITUDE = -0.20
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}
CSV_BACKUP_PATH = "weather_log.csv"


# ---------- STEP 1: EXTRACT ----------
def fetch_forecast():
    """Call the Open-Meteo API and return the raw JSON response."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": "temperature_2m_max,temperature_2m_min,windspeed_10m_max,precipitation_sum",
        "timezone": "Africa/Accra",
        "forecast_days": 7
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # throws an error if the API call failed
    return response.json()


# ---------- STEP 2: TRANSFORM ----------
def clean_forecast(raw_json):
    """Convert the columnar API response into a clean, row-based DataFrame."""
    daily = raw_json["daily"]

    df = pd.DataFrame({
        "forecast_date": daily["time"],
        "temp_max_c": daily["temperature_2m_max"],
        "temp_min_c": daily["temperature_2m_min"],
        "wind_speed_max_kmh": daily["windspeed_10m_max"],
        "precipitation_mm": daily["precipitation_sum"],
    })

    # Basic data quality checks
    df["forecast_date"] = pd.to_datetime(df["forecast_date"]).dt.date
    df = df.dropna()  # drop any row missing critical data

    return df


# ---------- STEP 3: LOAD (MySQL) ----------
def load_to_mysql(df):
    """Insert the cleaned rows into MySQL, skipping duplicates."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO fishing_conditions
            (forecast_date, temp_max_c, temp_min_c, wind_speed_max_kmh, precipitation_mm)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            temp_max_c = VALUES(temp_max_c),
            temp_min_c = VALUES(temp_min_c),
            wind_speed_max_kmh = VALUES(wind_speed_max_kmh),
            precipitation_mm = VALUES(precipitation_mm)
    """

    rows = df.itertuples(index=False, name=None)
    cursor.executemany(insert_query, list(rows))
    conn.commit()

    print(f"Inserted/updated {cursor.rowcount} rows into MySQL.")
    cursor.close()
    conn.close()


# ---------- STEP 4: LOAD (CSV backup) ----------
def save_csv_backup(df):
    """Append the cleaned data to a local CSV as a simple backup/audit trail."""
    df.to_csv(CSV_BACKUP_PATH, mode="a", header=False, index=False)
    print(f"Backed up {len(df)} rows to {CSV_BACKUP_PATH}")


# ---------- MAIN PIPELINE ----------
def run_pipeline():
    print(f"[{datetime.now()}] Starting fishing weather pipeline...")
    raw = fetch_forecast()
    clean_df = clean_forecast(raw)
    load_to_mysql(clean_df)
    save_csv_backup(clean_df)
    print(f"[{datetime.now()}] Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()


#------------------------ ERROR HANDLING ------------------------
def run_pipeline():
    try:
        print(f"[{datetime.now()}] Starting fishing weather pipeline...")
        raw = fetch_forecast()
        clean_df = clean_forecast(raw)
        load_to_mysql(clean_df)
        save_csv_backup(clean_df)
        print(f"[{datetime.now()}] Pipeline complete.")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API request failed: {e}")
    except mysql.connector.Error as e:
        print(f"[ERROR] Database error: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected failure: {e}")