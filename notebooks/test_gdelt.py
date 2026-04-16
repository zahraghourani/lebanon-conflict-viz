import requests
import pandas as pd
from io import StringIO
import time
from datetime import datetime, timedelta

QUERY = "war+airstrike+ceasefire+attack+conflict"
TIMESPAN = "15m"

# Dynamic date range
START_DATE = '2024-01-01'
END_DATE = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

def fetch_gdelt(mode, label):
    """
    Fetch GDELT data with robust error handling.
    
    Args:
        mode (str): GDELT mode (timelinetone, timelinevol, etc.)
        label (str): Human-readable label for logging
        
    Returns:
        pd.DataFrame: Processed data with date and value columns
    """
    print(f"📊 Fetching {label}...", end=" ", flush=True)
    
    try:
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={QUERY}"
            f"&mode={mode}"
            f"&format=csv"
            f"&timespan={TIMESPAN}"
         )
        
        # Fetch with timeout
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        text = response.text.strip()
        
        if not text:
            print("⚠️  Empty response")
            return pd.DataFrame()
        
        # Parse CSV robustly — skip header, take first 3 columns
        rows = []
        for i, line in enumerate(text.split('\n')):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip header row
            if i == 0 and line.startswith('date'):
                continue
            
            # Parse columns
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    rows.append({
                        'date': parts[0],
                        'value': parts[2]  # Third column is the value
                    })
                except (IndexError, ValueError):
                    continue
        
        if not rows:
            print("⚠️  No valid data rows")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Remove invalid rows
        df = df.dropna()
        df = df[df['value'] != 0]
        
        # Filter by date range
        start = pd.to_datetime(START_DATE)
        end = pd.to_datetime(END_DATE)
        df = df[(df['date'] >= start) & (df['date'] <= end)]
        
        # Sort and reset index
        df = df.sort_values('date').reset_index(drop=True)
        
        if df.empty:
            print("⚠️  No data in date range")
            return df
        
        print(f"✅ {len(df)} rows ({df['date'].min().date()} → {df['date'].max().date()})")
        return df
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout (API slow)")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        return pd.DataFrame()


# ── FETCH DATA ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("🔍 GDELT Data Fetcher")
print("="*60)
print(f"Query: {QUERY}")
print(f"Timespan: {TIMESPAN}")
print(f"Date range: {START_DATE} → {END_DATE}")
print("="*60 + "\n")

df_tone = fetch_gdelt("timelinetone", "Tone")
time.sleep(1)

df_vol = fetch_gdelt("timelinevol", "Volume")

# ── SAVE DATA ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("💾 Saving Data")
print("="*60)

if not df_tone.empty:
    df_tone.rename(columns={'value': 'tone'}, inplace=True)
    df_tone.to_csv('data/processed/gdelt_tone.csv', index=False)
    print(f"✅ Tone saved → data/processed/gdelt_tone.csv")
    print(f"   Avg tone: {df_tone['tone'].mean():.2f}")
    print(f"   Most negative: {df_tone.loc[df_tone['tone'].idxmin(), 'date'].date()}")
else:
    print("⚠️  Tone data is empty")

if not df_vol.empty:
    df_vol.rename(columns={'value': 'volume'}, inplace=True)
    df_vol.to_csv('data/processed/gdelt_volume.csv', index=False)
    print(f"✅ Volume saved → data/processed/gdelt_volume.csv")
    print(f"   Peak coverage: {df_vol.loc[df_vol['volume'].idxmax(), 'date'].date()}")
else:
    print("⚠️  Volume data is empty")

# ── SUMMARY ────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("✅ GDELT Data Fetch Complete")
print("="*60)
print(f"  Tone points  : {len(df_tone) if not df_tone.empty else 0}")
print(f"  Volume points: {len(df_vol) if not df_vol.empty else 0}")
print("="*60 + "\n")
