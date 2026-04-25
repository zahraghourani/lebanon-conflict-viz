import pandas as pd
import os
from textblob import TextBlob
import sys

def get_polarity(text):
    if not isinstance(text, str) or text.strip() == '':
        return 0.0
    return TextBlob(text).sentiment.polarity

def main():
    input_file = "data/raw/reddit_posts_middle_east.csv"
    output_file = "data/processed/reddit_posts_with_sentiment.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # --- DATA CLEANING ---
    print("Cleaning data...")
    # 1. Handle missing dates
    df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
    df = df.dropna(subset=['created_date'])
    
    # 2. Clean scores
    df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0)
    
    # 3. Add derived fields
    df['year_month'] = df['created_date'].dt.strftime('%Y-%m')
    
    # 4. Ensure text columns exist and are strings
    for col in ['title', 'selftext']:
        if col not in df.columns:
            df[col] = ''
        else:
            df[col] = df[col].fillna('').astype(str)
            
    # 5. Drop very low engagement noise (as per original logic)
    df = df[df['score'] >= 1].copy()
    
    # --- SENTIMENT CALCULATION ---
    print(f"Calculating sentiment for {len(df)} posts. This may take a minute...")
    df['sentiment'] = df['title'].apply(get_polarity)
    
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"Saved cleaned data with pre-calculated sentiment to {output_file}")

if __name__ == "__main__":
    main()
