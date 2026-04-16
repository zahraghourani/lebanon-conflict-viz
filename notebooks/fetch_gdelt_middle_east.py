import requests
import pandas as pd
import time
import os

os.makedirs("data/processed", exist_ok=True)

# ── STRATEGY ──────────────────────────────────────────────────────────────────
# GDELT's date-range API is flaky and often returns no data for older chunks.
# Most reliable approach: use timespan parameter with a simple short query.
# timespan=24m gives us ~2 years back from today which covers Jan 2024 → Apr 2025.
# We run 3 different queries and merge results for better coverage.

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

QUERIES = [
    ("conflict",  "war airstrike attack ceasefire"),
    ("levant",    "lebanon gaza palestine syria"),
    ("gulf",      "yemen iraq iran"),
]


def fetch(query_str, mode, label, retries=3):
    url = (
        f"{BASE_URL}"
        f"?query={requests.utils.quote(query_str)}"
        f"&mode={mode}"
        f"&format=csv"
        f"&timespan=24m"
    )

    for attempt in range(1, retries + 1):
        try:
            print(f"  [{label}] attempt {attempt}...", end=" ", flush=True)
            time.sleep(10)
            r = requests.get(url, timeout=120)

            lines = [l for l in r.text.strip().split('\n') if l.strip()]
            if len(lines) <= 1:
                print("no data.")
                return pd.DataFrame()

            rows = [l.split(',') for l in lines[1:]]
            df = pd.DataFrame(rows, columns=['date', 'series', 'value'])
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['date', 'value'])
            df = df[df['value'] != 0]

            # keep only Jan 2024 → Apr 2025
            df = df[
                (df['date'] >= '2024-01-01') &
                (df['date'] <= '2025-04-14')
            ]

            print(f"{len(df)} rows ✓")
            return df

        except requests.exceptions.Timeout:
            print(f"timeout.", end=" ")
            if attempt < retries:
                print(f"waiting 20s...")
                time.sleep(20)
            else:
                print("skipping.")
                return pd.DataFrame()

        except Exception as e:
            print(f"error: {e}")
            time.sleep(15)

    return pd.DataFrame()


def fetch_mode(mode, col_name):
    print(f"\n━━━ GDELT {col_name.upper()} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    frames = []

    for label, query in QUERIES:
        df = fetch(query, mode, label)
        if not df.empty:
            frames.append(df)
        time.sleep(8)

    if not frames:
        print("  ✗ No data collected.")
        return pd.DataFrame()

    # merge: for same date across queries, take the mean
    combined = (
        pd.concat(frames, ignore_index=True)
        .groupby('date')['value']
        .mean()
        .reset_index()
        .rename(columns={'value': col_name})
        .sort_values('date')
        .reset_index(drop=True)
    )

    print(f"\n  ✓ {len(combined)} data points")
    print(f"  Range: {combined['date'].min().date()} → {combined['date'].max().date()}")
    return combined


# ── RUN ───────────────────────────────────────────────────────────────────────
df_tone = fetch_mode("timelinetone", "tone")
if not df_tone.empty:
    df_tone.to_csv("data/processed/gdelt_tone.csv", index=False)
    print(f"  Avg tone         : {df_tone['tone'].mean():.2f}")
    print(f"  Most negative day: {df_tone.loc[df_tone['tone'].idxmin(), 'date'].date()}")
    print(f"  Saved → data/processed/gdelt_tone.csv ✓")

df_vol = fetch_mode("timelinevol", "volume")
if not df_vol.empty:
    df_vol.to_csv("data/processed/gdelt_volume.csv", index=False)
    print(f"  Peak day         : {df_vol.loc[df_vol['volume'].idxmax(), 'date'].date()}")
    print(f"  Saved → data/processed/gdelt_volume.csv ✓")

print("\n══════════════════════════════════════════")
print("GDELT PULL COMPLETE")
print(f"  Tone points  : {len(df_tone) if not df_tone.empty else 0}")
print(f"  Volume points: {len(df_vol) if not df_vol.empty else 0}")
if not df_tone.empty:
    print(f"  Tone range   : {df_tone['date'].min().date()} → {df_tone['date'].max().date()}")
if not df_vol.empty:
    print(f"  Volume range : {df_vol['date'].min().date()} → {df_vol['date'].max().date()}")
print("══════════════════════════════════════════")