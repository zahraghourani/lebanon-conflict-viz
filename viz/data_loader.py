# all data loading and caching
import streamlit as st
import pandas as pd
import os


@st.cache_data(ttl=3600)
def load_acled():
    """Load and preprocess ACLED conflict event data."""
    filepath = "data/raw/acled_middle_east.csv"
    
    if not os.path.exists(filepath):
        st.error(f"❌ Data file not found: {filepath}. Please run the data collection scripts first.")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(filepath, low_memory=False)
        
        # Validate required columns
        required_cols = ['event_date', 'fatalities', 'latitude', 'longitude', 'country', 'event_type']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.warning(f"⚠️ Missing columns in ACLED data: {missing}")
        
        df['event_date']     = pd.to_datetime(df['event_date'], errors='coerce')
        df['fatalities']     = pd.to_numeric(df['fatalities'], errors='coerce').fillna(0).astype(int)
        df['latitude']       = pd.to_numeric(df['latitude'],   errors='coerce')
        df['longitude']      = pd.to_numeric(df['longitude'],  errors='coerce')
        
        # Remove rows with invalid coordinates or dates
        df = df.dropna(subset=['latitude', 'longitude', 'event_date'])
        
        df['fatalities_size'] = df['fatalities'] + 1
        df['year_month']     = df['event_date'].dt.strftime('%Y-%m')
        df['month']          = df['event_date'].dt.to_period('M').astype(str)
        
        # Fix Palestine naming for consistency
        df['country'] = df['country'].replace(['Palestine', 'Israel'], 'Occupied Palestine')
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading ACLED data: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_reddit():
    """Load and preprocess Reddit posts data."""
    # Try to load pre-calculated sentiment first for performance
    processed_path = "data/processed/reddit_posts_with_sentiment.csv"
    raw_path = "data/raw/reddit_posts_middle_east.csv"
    
    filepath = processed_path if os.path.exists(processed_path) else raw_path
    
    if not os.path.exists(filepath):
        st.warning(f"⚠️ Reddit posts file not found: {filepath}")
        return pd.DataFrame()
    
    try:
        posts = pd.read_csv(filepath)
        
        # --- DATA CLEANING (Ensures consistency even if raw file is loaded) ---
        posts['created_date'] = pd.to_datetime(posts['created_date'], errors='coerce')
        posts = posts.dropna(subset=['created_date'])
        
        posts['score']        = pd.to_numeric(posts['score'],        errors='coerce').fillna(0)
        posts['year_month']   = posts['created_date'].dt.strftime('%Y-%m')
        
        # Ensure title and selftext columns exist
        for col in ['title', 'selftext']:
            if col not in posts.columns:
                posts[col] = ''
            else:
                posts[col] = posts[col].fillna('').astype(str)
        
        # Drop very low engagement noise
        posts = posts[posts['score'] >= 1].copy()
        
        return posts
    except Exception as e:
        st.warning(f"⚠️ Error loading Reddit posts: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_reddit_comments():
    """Load and preprocess Reddit comments data."""
    filepath = "data/raw/reddit_comments_middle_east.csv"
    
    if not os.path.exists(filepath):
        st.warning(f"⚠️ Reddit comments file not found: {filepath}")
        return pd.DataFrame()
    
    try:
        comments = pd.read_csv(filepath)
        
        # --- DATA CLEANING ---
        comments['created_date'] = pd.to_datetime(comments['created_date'], errors='coerce')
        comments = comments.dropna(subset=['created_date'])
        
        comments['score']        = pd.to_numeric(comments['score'], errors='coerce').fillna(0)
        comments['year_month']   = comments['created_date'].dt.strftime('%Y-%m')
        
        return comments
    except Exception as e:
        st.warning(f"⚠️ Error loading Reddit comments: {str(e)}")
        return pd.DataFrame()
