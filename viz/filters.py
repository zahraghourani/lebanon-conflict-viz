# sidebar filters logic
import streamlit as st
import pandas as pd
from datetime import date


def render_filters(acled: pd.DataFrame, posts: pd.DataFrame):
    """
    Renders all sidebar filters and returns filtered acled + reddit dataframes.
    Edit this file to add/remove/change any filter.
    """
    st.sidebar.header("🔎 Filters")

    # ── COUNTRY ───────────────────────────────────────────────
    all_countries = sorted(acled['country'].dropna().unique())
    sel_countries = st.sidebar.multiselect(
        "Country",
        all_countries,
        default=all_countries,
        help="Filter by country"
    )

    # ── REGION (admin1) — cascades from country ───────────────
    country_data = acled[acled['country'].isin(sel_countries)]
    all_regions  = sorted(country_data['admin1'].dropna().unique())
    sel_regions  = st.sidebar.multiselect(
        "Region",
        all_regions,
        default=all_regions,
        help="Regions update based on selected countries"
    )

    # ── EVENT TYPE ────────────────────────────────────────────
    all_types = sorted(acled['event_type'].dropna().unique())
    sel_types = st.sidebar.multiselect(
        "Event type",
        all_types,
        default=all_types
    )

    # ── DATE RANGE ────────────────────────────────────────────
    dmin   = acled['event_date'].min().date()
    dmax   = acled['event_date'].max().date()
    drange = st.sidebar.date_input(
        "Date range",
        value=(dmin, dmax),
        min_value=dmin,
        max_value=dmax
    )

    st.sidebar.markdown("---")
    st.sidebar.info("💡 Click any dot on the map to drill into that location.")

    # ── APPLY FILTERS ─────────────────────────────────────────
    filtered_acled = acled[
        acled['country'].isin(sel_countries) &
        acled['admin1'].isin(sel_regions) &
        acled['event_type'].isin(sel_types)
    ].copy()

    if len(drange) == 2:
        filtered_acled = filtered_acled[
            (filtered_acled['event_date'].dt.date >= drange[0]) &
            (filtered_acled['event_date'].dt.date <= drange[1])
        ]

    # filter reddit by same date range and country keywords
    filtered_posts = posts.copy()
    if len(drange) == 2:
        filtered_posts = filtered_posts[
            (filtered_posts["created_date"].dt.date >= drange[0]) &
            (filtered_posts["created_date"].dt.date <= drange[1])
        ]

    # Further filter Reddit posts by country keywords if available
    if sel_countries:
        # Create a regex pattern to match any of the selected countries in the post title or selftext
        country_pattern = "|".join(sel_countries)
        filtered_posts = filtered_posts[
            filtered_posts["title"].str.contains(country_pattern, case=False, na=False) |
            filtered_posts["selftext"].str.contains(country_pattern, case=False, na=False)
        ]

    return filtered_acled, filtered_posts, sel_countries, drange