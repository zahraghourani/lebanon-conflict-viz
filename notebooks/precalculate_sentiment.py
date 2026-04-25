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
    
    print(f"Calculating sentiment for {len(df)} posts. This may take a minute...")
    # Use title for sentiment as in the original dashboard
    df['sentiment'] = df['title'].apply(get_polarity)
    
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"Saved pre-calculated sentiment to {output_file}")

if __name__ == "__main__":
    main()
