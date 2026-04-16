import requests
import pandas as pd
import time
import os
from datetime import datetime

# Pullpush.io — free Reddit archive, no API key needed
# Covers posts and comments up to late 2024
# Docs: https://pullpush.io

os.makedirs("data/raw", exist_ok=True)

BASE_URL = "https://api.pullpush.io/reddit"

# ── SEARCH CONFIG ─────────────────────────────────────────────────────────────

# Date range to match ACLED
DATE_FROM = int(datetime(2024, 1, 1).timestamp())
DATE_TO   = int(datetime(2025, 4, 14).timestamp())

# Keywords covering all Middle East countries + conflict terms
KEYWORDS = [
    # Country/region specific
    "Lebanon conflict", "Lebanon war", "Lebanon airstrike",
    "Palestine war", "Gaza genocide", "Gaza airstrike", "West Bank",
    "Syria conflict", "Syria war", "Syria attack",
    "Yemen war", "Yemen airstrike", "Yemen ceasefire",
    "Iraq attack", "Iraq conflict",
    "Iran strike", "Iran attack",
    "Israel Palestine", "Israel Gaza",
    # Regional
    "Middle East conflict", "Middle East war",
]

# Target subreddits with most relevant conflict discussion
SUBREDDITS = [
    "worldnews",
    "news",
    "geopolitics",
    "MiddleEast",
    "Palestine",
    "Lebanon",
    "Syria",
    "Yemen",
    "Iran",
    "Iraq",
    "IsraelPalestine",
    "AskMiddleEast",
    "ArabIsraeliConflict",
]


def fetch_posts(subreddit, keyword, after, before, max_results=500):
    """Fetch posts from a subreddit matching a keyword in a date range."""
    all_posts = []
    params = {
        "subreddit": subreddit,
        "q": keyword,
        "after": after,
        "before": before,
        "size": 100,
        "sort": "desc",
        "sort_type": "created_utc",
    }

    while len(all_posts) < max_results:
        try:
            r = requests.get(
                f"{BASE_URL}/search/submission",
                params=params,
                timeout=15
            )
            data = r.json().get("data", [])
            if not data:
                break

            all_posts.extend(data)

            # paginate using oldest timestamp
            params["before"] = data[-1]["created_utc"]

            if len(data) < 100:
                break

            time.sleep(1)

        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(5)
            break

    return all_posts


def fetch_comments(subreddit, keyword, after, before, max_results=500):
    """Fetch comments from a subreddit matching a keyword."""
    all_comments = []
    params = {
        "subreddit": subreddit,
        "q": keyword,
        "after": after,
        "before": before,
        "size": 100,
        "sort": "desc",
        "sort_type": "created_utc",
    }

    while len(all_comments) < max_results:
        try:
            r = requests.get(
                f"{BASE_URL}/search/comment",
                params=params,
                timeout=15
            )
            data = r.json().get("data", [])
            if not data:
                break

            all_comments.extend(data)
            params["before"] = data[-1]["created_utc"]

            if len(data) < 100:
                break

            time.sleep(1)

        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(5)
            break

    return all_comments


# ── MAIN PULL ─────────────────────────────────────────────────────────────────

all_posts_data = []
all_comments_data = []

print("━━━ PULLPUSH REDDIT SCRAPER — MIDDLE EAST ━━━━━━━━━")
print(f"Date range: 2024-01-01 → 2025-04-14")
print(f"Subreddits: {len(SUBREDDITS)}")
print(f"Keywords  : {len(KEYWORDS)}\n")

for subreddit in SUBREDDITS:
    print(f"── r/{subreddit} ──────────────────────────")
    sub_posts = 0
    sub_comments = 0

    for keyword in KEYWORDS:
        # Posts
        posts = fetch_posts(subreddit, keyword, DATE_FROM, DATE_TO, max_results=200)
        for p in posts:
            all_posts_data.append({
                "id": p.get("id"),
                "subreddit": subreddit,
                "keyword": keyword,
                "title": p.get("title", ""),
                "selftext": p.get("selftext", ""),
                "author": p.get("author", ""),
                "score": p.get("score", 0),
                "upvote_ratio": p.get("upvote_ratio", 0),
                "num_comments": p.get("num_comments", 0),
                "created_utc": p.get("created_utc"),
                "created_date": datetime.utcfromtimestamp(p.get("created_utc", 0)).strftime('%Y-%m-%d') if p.get("created_utc") else None,
                "url": p.get("url", ""),
                "permalink": "https://reddit.com" + p.get("permalink", ""),
                "flair": p.get("link_flair_text", ""),
            })
        sub_posts += len(posts)

        # Top-level comments
        comments = fetch_comments(subreddit, keyword, DATE_FROM, DATE_TO, max_results=200)
        for c in comments:
            all_comments_data.append({
                "id": c.get("id"),
                "subreddit": subreddit,
                "keyword": keyword,
                "body": c.get("body", ""),
                "author": c.get("author", ""),
                "score": c.get("score", 0),
                "created_utc": c.get("created_utc"),
                "created_date": datetime.utcfromtimestamp(c.get("created_utc", 0)).strftime('%Y-%m-%d') if c.get("created_utc") else None,
                "permalink": "https://reddit.com" + c.get("permalink", ""),
            })
        sub_comments += len(comments)

        time.sleep(0.5)

    print(f"  ✓ {sub_posts} posts, {sub_comments} comments\n")

# ── SAVE ──────────────────────────────────────────────────────────────────────

posts_df = pd.DataFrame(all_posts_data).drop_duplicates(subset=['id'])
comments_df = pd.DataFrame(all_comments_data).drop_duplicates(subset=['id'])

posts_df['created_date'] = pd.to_datetime(posts_df['created_date'], errors='coerce')
comments_df['created_date'] = pd.to_datetime(comments_df['created_date'], errors='coerce')

posts_df.to_csv("data/raw/reddit_posts_middle_east.csv", index=False)
comments_df.to_csv("data/raw/reddit_comments_middle_east.csv", index=False)

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("REDDIT PULL COMPLETE")
print(f"  Posts    : {len(posts_df):,} (saved → data/raw/reddit_posts_middle_east.csv)")
print(f"  Comments : {len(comments_df):,} (saved → data/raw/reddit_comments_middle_east.csv)")
if not posts_df.empty:
    print(f"  Date range: {posts_df['created_date'].min().date()} → {posts_df['created_date'].max().date()}")
print(f"\n  Top subreddits by post count:")
print(posts_df['subreddit'].value_counts().head(10).to_string())
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")