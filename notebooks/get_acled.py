import requests
import pandas as pd
from io import StringIO
import os
import time
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("ACLED_EMAIL")
PASSWORD = os.getenv("ACLED_PASSWORD")

COUNTRIES = [
    # Levant & core conflict zones
    "Lebanon",
    "Palestine",        # ACLED name → renamed to "Occupied Palestine" below
    "Syria",
    "Jordan",

    # Gulf & Arabian Peninsula
    "Yemen",
    "Saudi Arabia",
    "Iraq",
    "Kuwait",
    "Bahrain",
    "Qatar",
    "United Arab Emirates",
    "Oman",

    # North Africa (Middle East overlap)
    "Egypt",
    "Libya",

    # Greater Middle East
    "Iran",
    "Turkey",
]

DATE_FROM = "2024-01-01"
DATE_TO   = "2026-04-14"


def get_token():
    print("Getting ACLED token...")
    response = requests.post(
        "https://acleddata.com/oauth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": EMAIL,
            "password": PASSWORD,
            "grant_type": "password",
            "client_id": "acled"
        }
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print(f"Token received ✓\n")
    print(f"Pulling {len(COUNTRIES)} countries: {DATE_FROM} → {DATE_TO}\n")
    return token


def fetch_country(token, country):
    all_dfs = []
    page = 1
    total = 0

    print(f"── {country} ──────────────────────────")
    while True:
        print(f"  Fetching page {page}...", end=" ", flush=True)
        url = (
            "https://acleddata.com/api/acled/read"
            "?_format=csv"
            f"&country={requests.utils.quote(country)}"
            f"&event_date={DATE_FROM}|{DATE_TO}"
            "&event_date_where=BETWEEN"
            "&limit=5000"
            f"&page={page}"
        )
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        text = response.text.strip()
        if not text or len(text.split('\n')) <= 1:
            print("no more data.")
            break

        df = pd.read_csv(StringIO(text))
        if len(df) == 0:
            print("empty page.")
            break

        all_dfs.append(df)
        total += len(df)
        print(f"{len(df)} events (running total: {total})")

        if len(df) < 5000:
            print(f"  Last page reached for {country}.")
            break

        page += 1
        time.sleep(0.5)

    if not all_dfs:
        print(f"  WARNING: no data returned for {country}\n")
        return pd.DataFrame()

    country_df = pd.concat(all_dfs, ignore_index=True)
    print(f"  ✓ {country}: {len(country_df):,} total events\n")
    return country_df


def main():
    os.makedirs("data/raw", exist_ok=True)

    token = get_token()
    all_frames = []
    skipped = []

    for country in COUNTRIES:
        df = fetch_country(token, country)

        if df.empty:
            skipped.append(country)
            continue

        # rename Palestine → "Occupied Palestine" for display consistency
        if country == "Palestine":
            df["country"] = "Occupied Palestine"

        # save per-country file
        safe_name = country.lower().replace(" ", "_")
        out_path = f"data/raw/acled_{safe_name}.csv"
        df.to_csv(out_path, index=False)
        print(f"  Saved → {out_path}\n")

        all_frames.append(df)

    # ── combined file ──────────────────────────────────────────────────────
    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)

        # normalise column types
        combined["event_date"] = pd.to_datetime(combined["event_date"])
        combined["fatalities"] = pd.to_numeric(combined["fatalities"], errors="coerce").fillna(0).astype(int)
        combined["latitude"]   = pd.to_numeric(combined["latitude"],   errors="coerce")
        combined["longitude"]  = pd.to_numeric(combined["longitude"],  errors="coerce")

        combined.to_csv("data/raw/acled_middle_east.csv", index=False)

        print("\n══════════════════════════════════════════")
        print("COMBINED DATASET — BROADER MIDDLE EAST")
        print(f"  Total events    : {len(combined):,}")
        print(f"  Date range      : {combined['event_date'].min().date()} → {combined['event_date'].max().date()}")
        print(f"  Countries       :\n{combined['country'].value_counts().to_string()}")
        print(f"  Event types     :\n{combined['event_type'].value_counts().to_string()}")
        print(f"  Total fatalities: {combined['fatalities'].sum():,}")
        if skipped:
            print(f"\n  Skipped (no data): {', '.join(skipped)}")
        print("══════════════════════════════════════════")
        print("Saved → data/raw/acled_middle_east.csv ✓")
    else:
        print("ERROR: No data collected for any country.")


if __name__ == "__main__":
    main()