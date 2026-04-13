import requests
import pandas as pd
from io import StringIO
import time

time.sleep(10)

print("Fetching tone data...")
url_tone = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=lebanon%20war%20airstrike%20ceasefire"
    "&mode=timelinetone"
    "&format=csv"
    "&timespan=6m"
)
r1 = requests.get(url_tone)
df_tone = pd.read_csv(StringIO(r1.text))
df_tone.columns = ['date', 'series', 'value']
df_tone['type'] = 'tone'
df_tone = df_tone[df_tone['value'] != 0]
print(f"Tone: {len(df_tone)} days ✓")

time.sleep(10)

print("Fetching volume data...")
url_vol = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=lebanon%20war%20airstrike%20ceasefire"
    "&mode=timelinevol"
    "&format=csv"
    "&timespan=6m"
)
r2 = requests.get(url_vol)
df_vol = pd.read_csv(StringIO(r2.text))
df_vol.columns = ['date', 'series', 'value']
df_vol['type'] = 'volume'
df_vol = df_vol[df_vol['value'] != 0]
print(f"Volume: {len(df_vol)} days ✓")

time.sleep(10)

print("Fetching geographic focus data...")
url_geo = (
    "https://api.gdeltproject.org/api/v2/doc/doc"
    "?query=lebanon%20war%20airstrike%20ceasefire"
    "&mode=timelinevolraw"
    "&format=csv"
    "&timespan=6m"
)
r3 = requests.get(url_geo)
print(f"Geo preview:\n{r3.text[:300]}")

# Save both clean datasets
df_tone['date'] = pd.to_datetime(df_tone['date'])
df_vol['date'] = pd.to_datetime(df_vol['date'])

df_tone.to_csv('data/processed/gdelt_tone.csv', index=False)
df_vol.to_csv('data/processed/gdelt_volume.csv', index=False)

print("\nAll saved!")
print(f"Tone range: {df_tone['date'].min().date()} to {df_tone['date'].max().date()}")
print(f"Volume range: {df_vol['date'].min().date()} to {df_vol['date'].max().date()}")
print(f"\nPeak volume day: {df_vol.loc[df_vol['value'].idxmax(), 'date'].date()}")
print(f"Most negative tone day: {df_tone.loc[df_tone['value'].idxmin(), 'date'].date()}")