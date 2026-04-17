# reddit sentiment analysis
import pandas as pd
import streamlit as st

# TextBlob for lightweight sentiment — no model download needed
# polarity: -1 (very negative) → 0 (neutral) → +1 (very positive)

@st.cache_data(ttl=3600)
def compute_sentiment(posts: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a sentiment polarity score to each Reddit post based on its title.
    Returns the posts dataframe with a new 'sentiment' column.
    Edit the source column here if you want to analyze selftext instead.
    """
    try:
        from textblob import TextBlob
    except ImportError:
        st.warning("textblob not installed. Run: pip install textblob")
        posts['sentiment'] = 0.0
        return posts

    def get_polarity(text):
        if not isinstance(text, str) or text.strip() == '':
            return 0.0
        return TextBlob(text).sentiment.polarity

    posts = posts.copy()
    posts['sentiment'] = posts['title'].apply(get_polarity)
    return posts


def get_daily_sentiment(posts: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates sentiment by day — returns daily avg sentiment and post count.
    Used for the sentiment line chart (replaces GDELT tone).
    """
    posts = posts.dropna(subset=['created_date', 'sentiment'])
    daily = (
        posts.groupby(posts['created_date'].dt.date)
        .agg(
            avg_sentiment=('sentiment', 'mean'),
            post_count=('id', 'count'),
            avg_score=('score', 'mean')
        )
        .reset_index()
        .rename(columns={'created_date': 'date'})
    )
    daily['date'] = pd.to_datetime(daily['date'])
    # 7-day rolling average to smooth the line
    daily = daily.sort_values('date')
    daily['sentiment_7d'] = daily['avg_sentiment'].rolling(7, min_periods=1).mean()
    return daily


def get_monthly_volume(posts: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    """
    Combines post + comment counts by month.
    Used for the volume area chart (replaces GDELT volume).
    """
    post_monthly = (
        posts.groupby('year_month')
        .size()
        .reset_index(name='posts')
    )
    comment_monthly = (
        comments.groupby('year_month')
        .size()
        .reset_index(name='comments')
    )
    monthly = post_monthly.merge(comment_monthly, on='year_month', how='outer').fillna(0)
    monthly['total'] = monthly['posts'] + monthly['comments']
    monthly = monthly.sort_values('year_month').reset_index(drop=True)
    return monthly