import requests
import pandas as pd

LATITUDE = 5.55
LONGITUDE = -0.20

def fetch_historical_weather(start_date, end_date):
    """Pull actual recorded weather for a past date range (not forecast)."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,windspeed_10m_max,precipitation_sum",
        "timezone": "Africa/Accra"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    daily = response.json()["daily"]

    return pd.DataFrame({
        "date": pd.to_datetime(daily["time"]).date,
        "temp_max_c": daily["temperature_2m_max"],
        "wind_speed_max_kmh": daily["windspeed_10m_max"],
        "precipitation_mm": daily["precipitation_sum"],
    })


def load_sales_data(csv_path):
    """Load your sales CSV and aggregate total sales per day."""
    sales = pd.read_csv(csv_path)
    sales["Date"] = pd.to_datetime(sales["Date"]).dt.date
    daily_sales = sales.groupby("Date")["Total_Amount_GHS"].sum().reset_index()
    daily_sales.columns = ["date", "total_sales_ghs"]
    return daily_sales


def main():
    # Match this range to whatever dates your sales CSV actually covers
    weather = fetch_historical_weather("2026-08-01", "2026-08-06")
    sales = load_sales_data("usam_sales_export_2026-08-06.csv")

    merged = pd.merge(sales, weather, on="date", how="inner")
    merged = merged.sort_values("date")

    print(merged.to_string(index=False))


    wind_corr = merged["total_sales_ghs"].corr(merged["wind_speed_max_kmh"])
    rain_corr = merged["total_sales_ghs"].corr(merged["precipitation_mm"])
    print(f"\nCorrelation between wind speed and sales: {wind_corr:.3f}")
    print(f"Correlation between precipitation and sales: {rain_corr:.3f}")
    # correlation = merged["total_sales_ghs"].corr(merged["wind_speed_max_kmh"])
    # print(f"\nCorrelation between wind speed and sales: {correlation:.3f}")


if __name__ == "__main__":
    main()


#--------------- FETCH MARINE API--------------------------
def fetch_marine_conditions(start_date, end_date):
    """Pull historical marine conditions — wave height, direction, period."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "wave_height_max,wave_period_max",
        "timezone": "Africa/Accra"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    daily = response.json()["daily"]

    return pd.DataFrame({
        "date": pd.to_datetime(daily["time"]).date,
        "wave_height_m": daily["wave_height_max"],
        "wave_period_s": daily["wave_period_max"],
    })


def main():
    weather = fetch_historical_weather("2026-08-01", "2026-08-06")
    marine = fetch_marine_conditions("2026-08-01", "2026-08-06")
    sales = load_sales_data("usam_sales_export_2026-08-06.csv")

    merged = pd.merge(sales, weather, on="date", how="inner")
    merged = pd.merge(merged, marine, on="date", how="inner")
    merged = merged.sort_values("date")

    print(merged.to_string(index=False))

    wind_corr = merged["total_sales_ghs"].corr(merged["wind_speed_max_kmh"])
    rain_corr = merged["total_sales_ghs"].corr(merged["precipitation_mm"])
    wave_corr = merged["total_sales_ghs"].corr(merged["wave_height_m"])
    print(f"\nCorrelation between wind speed and sales: {wind_corr:.3f}")
    print(f"Correlation between precipitation and sales: {rain_corr:.3f}")
    print(f"Correlation between wave height and sales: {wave_corr:.3f}")
