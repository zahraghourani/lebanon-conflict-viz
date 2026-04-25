import pandas as pd
import os
os.makedirs('data/processed', exist_ok=True)

# ACLED
acled = pd.read_csv('data/raw/acled_middle_east.csv', low_memory=False)
acled['event_date'] = pd.to_datetime(acled['event_date'])
acled['fatalities'] = pd.to_numeric(acled['fatalities'], errors='coerce').fillna(0).astype(int)
acled['latitude'] = pd.to_numeric(acled['latitude'], errors='coerce')
acled['longitude'] = pd.to_numeric(acled['longitude'], errors='coerce')
acled['country'] = acled['country'].replace({'Palestine': 'Occupied Palestine', 'Israel': 'Occupied Palestine'})
acled = acled.dropna(subset=['latitude','longitude','event_type'])
acled['year_month'] = acled['event_date'].dt.strftime('%Y-%m')
acled['fatalities_size'] = acled['fatalities'] + 1
acled['week'] = acled['event_date'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%b %d, %Y'))
acled['admin1'] = acled['admin1'].fillna(acled['country'])
acled.to_csv('data/processed/acled_clean.csv', index=False)
print(f'ACLED saved: {len(acled):,} rows')

# Reddit posts
posts = pd.read_csv('data/raw/reddit_posts_middle_east.csv')
posts['created_date'] = pd.to_datetime(posts['created_date'], errors='coerce')
posts['score'] = pd.to_numeric(posts['score'], errors='coerce').fillna(0)
posts = posts.drop_duplicates(subset=['id'])
posts = posts[posts['score'] >= 1].dropna(subset=['title'])
posts['year_month'] = posts['created_date'].dt.strftime('%Y-%m')
posts.to_csv('data/processed/reddit_posts_clean.csv', index=False)
print(f'Posts saved: {len(posts):,} rows')

# Reddit comments
comments = pd.read_csv('data/raw/reddit_comments_middle_east.csv')
comments['created_date'] = pd.to_datetime(comments['created_date'], errors='coerce')
comments['score'] = pd.to_numeric(comments['score'], errors='coerce').fillna(0)
comments = comments.drop_duplicates(subset=['id'])
comments = comments[~comments['body'].isin(['[deleted]','[removed]'])]
comments = comments.dropna(subset=['body'])
comments['year_month'] = comments['created_date'].dt.strftime('%Y-%m')
comments.to_csv('data/processed/reddit_comments_clean.csv', index=False)
print(f'Comments saved: {len(comments):,} rows')

print('Done — data/processed/ is restored!')
