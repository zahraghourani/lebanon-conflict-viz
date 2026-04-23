# main app, just imports and runs everything
import streamlit as st
import pandas as pd

# ── local modules — edit each file independently ──────────────────────────────
from data_loader import load_acled, load_reddit, load_reddit_comments
from filters    import render_filters
from sentiment  import compute_sentiment, get_daily_sentiment, get_monthly_volume
from charts     import (
    make_map,
    make_event_timeline,
    make_country_timeline,
    make_dot_plot,
    make_fatalities_monthly,
    make_fatalities_by_country,
    make_sentiment_chart,
    make_volume_chart,
    make_top_posts_table,
    make_event_type_heatmap,
    make_fatality_intensity_scatter,
    EVENT_COLORS,
)

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Middle East Conflict Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stat-box {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 14px 18px;
        text-align: center;
    }
    .stat-label { font-size: 12px; color: #666; margin-bottom: 4px; }
    .stat-value { font-size: 24px; font-weight: 600; color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────

with st.spinner("Loading data..."):
    acled    = load_acled()
    posts    = load_reddit()
    comments = load_reddit_comments()
    posts    = compute_sentiment(posts)

# ── SIDEBAR FILTERS ───────────────────────────────────────────────────────────

filtered, filtered_posts, sel_countries, drange = render_filters(acled, posts)

# ── CLICK STATE ───────────────────────────────────────────────────────────────

if 'clicked_location' not in st.session_state:
    st.session_state.clicked_location = None

# ── HEADER ────────────────────────────────────────────────────────────────────

st.title("🌍 Middle East Conflict Dashboard")
st.caption(
    "ACLED verified conflict events · Reddit public sentiment · "
    "Jan 2024 – Apr 2025 · 17 countries · 112,000+ events"
)

# ── METRICS ROW ───────────────────────────────────────────────────────────────

display_data = filtered.copy()
if st.session_state.clicked_location:
    display_data = filtered[filtered['location'] == st.session_state.clicked_location]

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Events",           f"{len(display_data):,}")
m2.metric("Fatalities",       f"{int(display_data['fatalities'].sum()):,}")
m3.metric("Countries",        display_data['country'].nunique())
m4.metric("Regions",          display_data['admin1'].nunique())
m5.metric("Reddit posts",     f"{len(filtered_posts):,}")
m6.metric("Showing",
          st.session_state.clicked_location
          if st.session_state.clicked_location else "All locations")

if st.session_state.clicked_location:
    if st.button(f"✕ Clear: {st.session_state.clicked_location}"):
        st.session_state.clicked_location = None
        st.rerun()

st.markdown("---")

# ── SECTION 1 — MAP ───────────────────────────────────────────────────────────

st.subheader("📍 Where — Conflict Events Map")
st.caption("Click any dot to drill into that location and filter all charts below.")

col_map, col_stats = st.columns([3, 1])

with col_map:
    fig_map = make_map(filtered)
    clicked = st.plotly_chart(
        fig_map,
        use_container_width=True,
        on_select="rerun",
        key="map_chart"
    )
    if clicked and clicked.get("selection") and clicked["selection"].get("points"):
        point = clicked["selection"]["points"][0]
        loc   = point.get("hovertext") or point.get("customdata", [None])[0]
        if loc and loc != st.session_state.clicked_location:
            st.session_state.clicked_location = loc
            st.rerun()

with col_stats:
    st.markdown("##### Location stats")
    if st.session_state.clicked_location:
        loc_data = filtered[filtered['location'] == st.session_state.clicked_location]
        st.markdown(f"**{st.session_state.clicked_location}**")
        st.metric("Events",     len(loc_data))
        st.metric("Fatalities", int(loc_data['fatalities'].sum()))
        if len(loc_data) > 0:
            st.metric("Country", loc_data['country'].iloc[0])
            st.metric("Region",  loc_data['admin1'].iloc[0])

        st.markdown("**Event types:**")
        for etype, count in loc_data['event_type'].value_counts().items():
            color = EVENT_COLORS.get(etype, '#888')
            st.markdown(
                f'<span style="color:{color}">■</span> {etype}: **{count}**',
                unsafe_allow_html=True
            )

        st.markdown("**Recent events:**")
        for _, row in loc_data.sort_values('event_date', ascending=False).head(3).iterrows():
            st.caption(f"{row['event_date'].date()} · {row['event_type']} · {int(row['fatalities'])} fatalities")
    else:
        st.markdown("**Top locations:**")
        top_locs = (
            filtered.groupby('location')
            .agg(events=('event_type', 'count'), fatalities=('fatalities', 'sum'))
            .sort_values('events', ascending=False)
            .head(7)
        )
        for loc, row in top_locs.iterrows():
            st.markdown(f"**{loc}** — {row['events']} events, {int(row['fatalities'])} fatalities")

st.markdown("---")

# ── SECTION 2 — TIMELINE ──────────────────────────────────────────────────────

st.subheader("📅 When — Conflict Timeline")

tab1, tab2 = st.tabs(["By event type", "By country"])

with tab1:
    st.altair_chart(make_event_timeline(filtered), use_container_width=True)

with tab2:
    st.altair_chart(make_country_timeline(filtered), use_container_width=True)

st.markdown("---")

# ── SECTION 3 — FATALITIES & DOT PLOT ────────────────────────────────────────

st.subheader("💔 Human Cost — Fatalities & Intensity")

col_f1, col_f2 = st.columns(2)
with col_f1:
    st.altair_chart(make_fatalities_monthly(filtered),    use_container_width=True)
with col_f2:
    st.altair_chart(make_fatalities_by_country(filtered), use_container_width=True)

st.markdown("##### Events vs Fatalities by Country")
st.caption("Blue = event count (normalized), Red = fatality count (normalized). Gap shows lethality relative to activity.")
st.altair_chart(make_dot_plot(filtered), use_container_width=True)

st.markdown("---")

# ── SECTION 3B — ADVANCED ANALYSIS ────────────────────────────────────────────

st.subheader("🔬 Advanced Analysis")

tab_heat, tab_intensity = st.tabs(["Event Type Distribution", "Fatality Intensity"])

with tab_heat:
    st.caption("Heatmap showing which event types occur most frequently in each country.")
    st.altair_chart(make_event_type_heatmap(filtered), use_container_width=True)

with tab_intensity:
    st.caption("Scatter plot showing the lethality of events (fatalities per event) by country. Larger bubbles indicate higher total fatalities.")
    st.altair_chart(make_fatality_intensity_scatter(filtered), use_container_width=True)

st.markdown("---")

# ── SECTION 4 — REDDIT SENTIMENT ─────────────────────────────────────────────

st.subheader("💬 Public Voice — Reddit Sentiment & Volume")
st.caption("Sentiment derived from TextBlob polarity on Reddit post titles · -1 = very negative · +1 = very positive")

daily_sentiment = get_daily_sentiment(filtered_posts)
monthly_volume  = get_monthly_volume(filtered_posts, comments)

st.altair_chart(make_sentiment_chart(daily_sentiment), use_container_width=True)
st.altair_chart(make_volume_chart(monthly_volume),     use_container_width=True)

st.markdown("##### Most upvoted Reddit posts")
st.caption("Filtered by selected date range. Click permalink to view original post.")
top_posts = make_top_posts_table(filtered_posts, n=10)
st.dataframe(top_posts, use_container_width=True)

st.markdown("---")

# ── FOOTER ────────────────────────────────────────────────────────────────────

st.caption(
    "Sources: ACLED (acleddata.com) · Reddit via Pullpush.io · "
    "Sentiment: TextBlob · Built with Streamlit + Altair + Plotly · "
    "Conflict data Jan 2024 – Apr 2025 · "
    "Enhanced with improved filtering, error handling, and advanced analytics"
)