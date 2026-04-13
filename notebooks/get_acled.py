import requests
import pandas as pd
from io import StringIO
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("ACLED_EMAIL")
PASSWORD = os.getenv("ACLED_PASSWORD")

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
    token = response.json()["access_token"]
    print("Token received ✓")
    return token

def get_all_lebanon_data(token):
    all_dfs = []
    page = 1
    total = 0

    while True:
        print(f"Fetching page {page}...")
        url = (
            "https://acleddata.com/api/acled/read"
            "?_format=csv"
            "&country=Lebanon"
            "&event_date=2024-01-01|2026-04-14"
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

        text = response.text.strip()
        if not text or len(text.split('\n')) <= 1:
            print(f"No more data on page {page}. Done.")
            break

        df = pd.read_csv(StringIO(text))
        if len(df) == 0:
            break

        all_dfs.append(df)
        total += len(df)
        print(f"  Got {len(df)} events (total so far: {total})")

        if len(df) < 5000:
            print("Last page reached.")
            break

        page += 1

    return pd.concat(all_dfs, ignore_index=True)

token = get_token()
df = get_all_lebanon_data(token)

print(f"\nTotal events: {len(df)}")
print(f"Date range: {df['event_date'].min()} to {df['event_date'].max()}")
print(f"Event types:\n{df['event_type'].value_counts()}")

df.to_csv("data/raw/acled_lebanon.csv", index=False)
print("\nSaved to data/raw/acled_lebanon.csv ✓")