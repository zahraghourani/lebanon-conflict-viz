import requests
import pandas as pd
from io import StringIO
import time
import os

os.makedirs("data/processed", exist_ok=True)

# OR terms wrapped in () as GDELT requires
# Simple query — no startdatetime/enddatetime (flaky), instead we pull
# each quarter separately using timespan trick via GDELT's supported params
# GDELT date format: YYYYMMDDHHMMSS

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERY = "(lebanon+OR+palestine+OR+gaza+OR+syria+OR+yemen+OR+iraq)+conflict"

# Pull 4 quarters covering Jan 2024 → Apr 2025
CHUNKS = [
    ("20240101000000", "20240401000000", "Q1 2024"),
    ("20240401000000", "20240701000000", "Q2 2024"),
    ("20240701000000", "20241001000000", "Q3 2024"),
    ("20241001000000", "20250101000000", "Q4 2024"),
    ("20250101000000", "20250414000000", "Q1 2025"),
]


def fetch_chunk(mode, start, end, label):
    url = (
        f"{BASE}?query={QUERY}"
        f"&mode={mode}"
        f"&format=csv"
        f"&startdatetime={start}"
        f"&enddatetime={end}"
    )
    print(f"  {label}...", end=" ", flush=True)
    time.sleep(30)  # strict rate limit respect

    try:
        r = requests.get(url, timeout=120)
        text = r.text.strip()

        if not text or len(text) < 30:
            print(f"empty/error: {text[:100]}")
            return pd.DataFrame()

        if "limit" in text.lower():
            print(f"rate limited, waiting 60s...")
            time.sleep(60)
            r = requests.get(url, timeout=120)
            text = r.text.strip()

        if "OR" in text or "must be" in text or len(text) < 30:
            print(f"API error: {text[:100]}")
            return pd.DataFrame()

        df = pd.read_csv(StringIO(text))
        if df.shape[1] >= 2:
            df = df.iloc[:, :2]
            df.columns = ['date', 'value']
        else:
            print(f"bad shape: {df.shape}")
            return pd.DataFrame()

        df['date']  = pd.to_datetime(df['date'],  errors='coerce')
        df['value'] = pd.to_numeric(df['value'],  errors='coerce')
        df = df.dropna()
        df = df[df['value'] != 0]
        print(f"{len(df)} rows ✓")
        return df

    except Exception as e:
        print(f"error: {e}")
        return pd.DataFrame()


def fetch_all(mode, col_name):
    print(f"\n━━━ {col_name.upper()} ━━━━━━━━━━━━━━━━━━━━━━━━━━")
    frames = []
    for start, end, label in CHUNKS:
        df = fetch_chunk(mode, start, end, label)
        if not df.empty:
            frames.append(df)

    if not frames:
        print("  No data collected.")
        return pd.DataFrame()

    combined = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=['date'])
        .sort_values('date')
        .reset_index(drop=True)
        .rename(columns={'value': col_name})
    )
    print(f"\n  Total: {len(combined)} data points")
    print(f"  Range: {combined['date'].min().date()} → {combined['date'].max().date()}")
    return combined


print("=" * 50)
print("GDELT — Jan 2024 → Apr 2025")
print("Each chunk waits 30s — takes ~5 mins total")
print("=" * 50)

df_tone = fetch_all("timelinetone", "tone")
df_vol  = fetch_all("timelinevol",  "volume")

if not df_tone.empty:
    df_tone.to_csv("data/processed/gdelt_tone.csv", index=False)
    print(f"\n✓ Tone saved — avg: {df_tone['tone'].mean():.2f}")
    print(f"  Most negative day: {df_tone.loc[df_tone['tone'].idxmin(), 'date'].date()}")
else:
    print("\n⚠ No tone data saved")

if not df_vol.empty:
    df_vol.to_csv("data/processed/gdelt_volume.csv", index=False)
    print(f"\n✓ Volume saved — peak: {df_vol.loc[df_vol['volume'].idxmax(), 'date'].date()}")
else:
    print("\n⚠ No volume data saved")

print("\n" + "=" * 50)
print(f"DONE — Tone: {len(df_tone)} pts | Volume: {len(df_vol)} pts")
print("=" * 50)