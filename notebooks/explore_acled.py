import pandas as pd

df = pd.read_csv("data/raw/acled_lebanon.csv")

print(f"Total events: {len(df)}")
print(f"Date range: {df['event_date'].min()} to {df['event_date'].max()}")
print(f"\nEvent types:")
print(df['event_type'].value_counts())
print(f"\nTop locations:")
print(df['admin1'].value_counts().head(10))
print(f"\nTotal fatalities: {df['fatalities'].sum()}")
print(f"\nSample row:")
print(df[['event_date', 'event_type', 'sub_event_type', 
          'actor1', 'location', 'latitude', 
          'longitude', 'fatalities']].head(5))