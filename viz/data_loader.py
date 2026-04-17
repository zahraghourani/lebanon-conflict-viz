# all data loading and caching
import streamlit as st
import pandas as pd


@st.cache_data(ttl=3600)
def load_acled():
    df = pd.read_csv("data/raw/acled_middle_east.csv", low_memory=False)
    df['event_date']     = pd.to_datetime(df['event_date'])
    df['fatalities']     = pd.to_numeric(df['fatalities'], errors='coerce').fillna(0).astype(int)
    df['latitude']       = pd.to_numeric(df['latitude'],   errors='coerce')
    df['longitude']      = pd.to_numeric(df['longitude'],  errors='coerce')
    df['fatalities_size'] = df['fatalities'] + 1
    df['year_month']     = df['event_date'].dt.strftime('%Y-%m')
    df['month']          = df['event_date'].dt.to_period('M').astype(str)
    # fix Palestine naming
    df['country'] = df['country'].replace('Palestine', 'Occupied Palestine')
    return df


@st.cache_data(ttl=3600)
def load_reddit():
    posts = pd.read_csv("data/raw/reddit_posts_middle_east.csv")
    posts['created_date'] = pd.to_datetime(posts['created_date'], errors='coerce')
    posts['score']        = pd.to_numeric(posts['score'],        errors='coerce').fillna(0)
    posts['year_month']   = posts['created_date'].dt.strftime('%Y-%m')
    # drop very low engagement noise
    posts = posts[posts['score'] >= 1].copy()
    return posts


@st.cache_data(ttl=3600)
def load_reddit_comments():
    comments = pd.read_csv("data/raw/reddit_comments_middle_east.csv")
    comments['created_date'] = pd.to_datetime(comments['created_date'], errors='coerce')
    comments['score']        = pd.to_numeric(comments['score'], errors='coerce').fillna(0)
    comments['year_month']   = comments['created_date'].dt.strftime('%Y-%m')
    return comments