from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = FastAPI(title="Middle East Conflict API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_acled():
    df = pd.read_csv("data/processed/acled_clean.csv", low_memory=False)
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    if "fatalities_size" not in df.columns:
        df["fatalities_size"] = df["fatalities"] + 1
    return df


@lru_cache(maxsize=1)
def get_posts():
    df = pd.read_csv("data/processed/reddit_posts_clean.csv")
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    analyzer = SentimentIntensityAnalyzer()
    df["sentiment"] = df["title"].apply(
        lambda x: analyzer.polarity_scores(str(x))["compound"] if isinstance(x, str) else 0.0
    )
    return df


@lru_cache(maxsize=1)
def get_comments():
    df = pd.read_csv("data/processed/reddit_comments_clean.csv")
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    return df


def apply_filters(df, countries, event_types, date_from, date_to):
    if countries:
        df = df[df["country"].isin(countries)]
    if event_types:
        df = df[df["event_type"].isin(event_types)]
    if date_from:
        df = df[df["event_date"] >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df["event_date"] <= pd.Timestamp(date_to)]
    return df


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/api/filters/options")
def filter_options():
    acled = get_acled()
    return {
        "countries": sorted(acled["country"].dropna().unique().tolist()),
        "event_types": sorted(acled["event_type"].dropna().unique().tolist()),
        "date_min": acled["event_date"].min().strftime("%Y-%m-%d"),
        "date_max": acled["event_date"].max().strftime("%Y-%m-%d"),
    }


@app.get("/api/metrics")
def metrics(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    posts = get_posts()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    return {
        "total_events": int(len(acled)),
        "total_fatalities": int(acled["fatalities"].sum()),
        "total_countries": int(acled["country"].nunique()),
        "total_regions": int(acled["admin1"].nunique()),
        "reddit_posts": int(len(posts)),
    }


@app.get("/api/map/heatmap")
def map_heatmap(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    week: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)

    if week and "week" in acled.columns:
        week_df = acled[acled["week"] == week]
        if not week_df.empty:
            acled = week_df

    acled = acled.dropna(subset=["latitude", "longitude"])
    if len(acled) > 5000:
        acled = acled.sample(5000, random_state=42)

    return {
        "points": acled[["latitude", "longitude", "fatalities_size"]]
        .rename(columns={"latitude": "lat", "longitude": "lon", "fatalities_size": "weight"})
        .to_dict(orient="records")
    }


@app.get("/api/map/events")
def map_events(
    country: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    week: str = Query(None),
):
    acled = get_acled().copy()
    if country:
        acled = acled[acled["country"] == country]
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, None, event_types_list, date_from, date_to)

    if week and "week" in acled.columns:
        week_df = acled[acled["week"] == week]
        if not week_df.empty:
            acled = week_df

    acled = acled.dropna(subset=["latitude", "longitude"])
    if len(acled) > 2000:
        with_fat = acled[acled["fatalities"] > 0]
        without_fat = acled[acled["fatalities"] == 0]
        n_fat = min(len(with_fat), 1500)
        n_no_fat = min(len(without_fat), 2000 - n_fat)
        acled = pd.concat(
            [
                with_fat.sample(n_fat, random_state=42) if n_fat > 0 else pd.DataFrame(),
                without_fat.sample(n_no_fat, random_state=42) if n_no_fat > 0 else pd.DataFrame(),
            ]
        )

    acled["date_str"] = acled["event_date"].dt.strftime("%b %d, %Y")
    if "actor1" not in acled.columns:
        acled["actor1"] = "Unknown"
    acled["actor1"] = acled["actor1"].fillna("Unknown")
    cols = [
        "location",
        "latitude",
        "longitude",
        "event_type",
        "fatalities",
        "fatalities_size",
        "actor1",
        "date_str",
        "sub_event_type",
        "admin1",
        "country",
    ]
    cols = [c for c in cols if c in acled.columns]
    return {"events": acled[cols].to_dict(orient="records")}


@app.get("/api/weeks")
def get_weeks(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    weeks = sorted(acled["week"].dropna().unique().tolist()) if "week" in acled.columns else []
    return {"weeks": weeks}


@app.get("/api/timeline/events")
def timeline_events(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    monthly = acled.groupby(["year_month", "event_type"]).size().reset_index(name="count")
    return {"data": monthly.to_dict(orient="records")}


@app.get("/api/timeline/countries")
def timeline_countries(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    top6 = acled.groupby("country").size().sort_values(ascending=False).head(6).index.tolist()
    acled = acled[acled["country"].isin(top6)]
    monthly = acled.groupby(["year_month", "country"]).size().reset_index(name="count")
    return {"data": monthly.to_dict(orient="records")}


@app.get("/api/fatalities/monthly")
def fatalities_monthly(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    monthly = acled.groupby("year_month")["fatalities"].sum().reset_index()
    return {"data": monthly.to_dict(orient="records")}


@app.get("/api/fatalities/countries")
def fatalities_countries(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    fat = (
        acled.groupby("country")["fatalities"]
        .sum()
        .reset_index()
        .sort_values("fatalities", ascending=False)
    )
    return {"data": fat.to_dict(orient="records")}


@app.get("/api/dotplot")
def dotplot(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    agg = (
        acled.groupby("country")
        .agg(events=("event_type", "count"), fatalities=("fatalities", "sum"))
        .reset_index()
    )
    agg = agg[agg["events"] >= 10]
    if not agg.empty:
        agg["events_norm"] = (agg["events"] / agg["events"].max() * 100).round(1)
        agg["fatalities_norm"] = (agg["fatalities"] / agg["fatalities"].max() * 100).round(1)
    agg = agg.sort_values("fatalities", ascending=False)
    return {"data": agg.to_dict(orient="records")}


@app.get("/api/sentiment")
def sentiment():
    posts = get_posts()
    p = posts[["created_date", "sentiment"]].copy()
    p["date"] = p["created_date"].dt.date
    daily = (
        p.groupby("date")
        .agg(avg_sentiment=("sentiment", "mean"), post_count=("sentiment", "count"))
        .reset_index()
        .sort_values("date")
    )
    daily["sentiment_7d"] = daily["avg_sentiment"].rolling(7, min_periods=1).mean()
    daily["date"] = daily["date"].astype(str)
    return {"data": daily.to_dict(orient="records")}


@app.get("/api/volume")
def volume():
    posts = get_posts()
    comments = get_comments()
    post_monthly = posts.groupby("year_month").size().reset_index(name="posts")
    comment_monthly = comments.groupby("year_month").size().reset_index(name="comments")
    monthly = post_monthly.merge(comment_monthly, on="year_month", how="outer").fillna(0)
    monthly = monthly.sort_values("year_month")
    return {"data": monthly.to_dict(orient="records")}


@app.get("/api/top-posts")
def top_posts(date_from: str = Query(None), date_to: str = Query(None)):
    posts = get_posts().copy()
    if date_from:
        posts = posts[posts["created_date"] >= pd.Timestamp(date_from)]
    if date_to:
        posts = posts[posts["created_date"] <= pd.Timestamp(date_to)]
    cols = ["created_date", "subreddit", "title", "score", "num_comments", "sentiment", "permalink"]
    cols = [c for c in cols if c in posts.columns]
    top = posts[cols].sort_values("score", ascending=False).head(10)
    if "created_date" in top.columns:
        top["created_date"] = top["created_date"].dt.strftime("%b %d, %Y")
    if "sentiment" in top.columns:
        top["sentiment"] = top["sentiment"].round(3)
    return {"data": top.to_dict(orient="records")}


@app.get("/api/top-locations")
def top_locations(
    countries: str = Query(None),
    event_types: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    acled = get_acled().copy()
    countries_list = countries.split(",") if countries else None
    event_types_list = event_types.split(",") if event_types else None
    acled = apply_filters(acled, countries_list, event_types_list, date_from, date_to)
    top = (
        acled.groupby("location")
        .agg(events=("event_type", "count"), fatalities=("fatalities", "sum"))
        .sort_values("fatalities", ascending=False)
        .head(7)
        .reset_index()
    )
    return {"data": top.to_dict(orient="records")}


app.mount("/static", StaticFiles(directory="static"), name="static")
