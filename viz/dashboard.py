import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO
from dotenv import load_dotenv
import time

load_dotenv()

st.set_page_config(
    page_title="Lebanon Conflict Dashboard",
    page_icon="🇱🇧",
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

# ── DATA LOADERS ─────────────────────────────────────────────

@st.cache_data(ttl=900)
def load_gdelt_tone():
    time.sleep(15)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        "?query=lebanon%20war%20airstrike%20ceasefire"
        "&mode=timelinetone&format=csv&timespan=6m"
    )
    r = requests.get(url)
    lines = [l for l in r.text.strip().split('\n') if l.strip()]
    rows = [l.split(',') for l in lines[1:]]
    df = pd.DataFrame(rows, columns=['date', 'series', 'tone'])
    df['date'] = pd.to_datetime(df['date'])
    df['tone'] = pd.to_numeric(df['tone'], errors='coerce')
    return df.dropna().query("tone != 0")

@st.cache_data(ttl=900)
def load_gdelt_volume():
    time.sleep(15)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        "?query=lebanon%20war%20airstrike%20ceasefire"
        "&mode=timelinevol&format=csv&timespan=6m"
    )
    r = requests.get(url)
    lines = [l for l in r.text.strip().split('\n') if l.strip()]
    rows = [l.split(',') for l in lines[1:]]
    df = pd.DataFrame(rows, columns=['date', 'series', 'volume'])
    df['date'] = pd.to_datetime(df['date'])
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    return df.dropna().query("volume != 0")

@st.cache_data(ttl=3600)
def load_acled():
    df = pd.read_csv("data/raw/acled_lebanon.csv")
    df['event_date'] = pd.to_datetime(df['event_date'])
    df['month'] = df['event_date'].dt.to_period('M').astype(str)
    df['fatalities_size'] = df['fatalities'] + 1
    df['year_month'] = df['event_date'].dt.strftime('%Y-%m')
    return df

# ── LOAD ─────────────────────────────────────────────────────

with st.spinner("Loading data..."):
    gdelt_tone = load_gdelt_tone()
    gdelt_vol  = load_gdelt_volume()
    acled      = load_acled()

# ── HEADER ───────────────────────────────────────────────────

st.title("🇱🇧 Lebanon Conflict Dashboard")
st.caption("ACLED verified conflict events · GDELT real-time media sentiment · Refreshes every 15 min")

# ── SIDEBAR ──────────────────────────────────────────────────

st.sidebar.header("Filters")

all_regions = sorted(acled['admin1'].dropna().unique())
sel_regions = st.sidebar.multiselect("Region", all_regions, default=all_regions)

all_types = sorted(acled['event_type'].dropna().unique())
sel_types = st.sidebar.multiselect("Event type", all_types, default=all_types)

dmin = acled['event_date'].min().date()
dmax = acled['event_date'].max().date()
drange = st.sidebar.date_input("Date range", value=(dmin, dmax),
                                min_value=dmin, max_value=dmax)

st.sidebar.markdown("---")
st.sidebar.info("Click any dot on the map to filter all charts to that location.")

# ── FILTER ───────────────────────────────────────────────────

filtered = acled[
    acled['admin1'].isin(sel_regions) &
    acled['event_type'].isin(sel_types)
].copy()

if len(drange) == 2:
    filtered = filtered[
        (filtered['event_date'].dt.date >= drange[0]) &
        (filtered['event_date'].dt.date <= drange[1])
    ]

# ── CLICK STATE ──────────────────────────────────────────────

if 'clicked_location' not in st.session_state:
    st.session_state.clicked_location = None

# ── METRICS ──────────────────────────────────────────────────

display_data = filtered.copy()
if st.session_state.clicked_location:
    display_data = filtered[
        filtered['location'] == st.session_state.clicked_location
    ]

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Events", f"{len(display_data):,}")
m2.metric("Fatalities", f"{int(display_data['fatalities'].sum()):,}")
m3.metric("Regions", display_data['admin1'].nunique())
m4.metric("Avg media tone", f"{gdelt_tone['tone'].mean():.2f}")
m5.metric("Showing",
          st.session_state.clicked_location
          if st.session_state.clicked_location else "All locations")

if st.session_state.clicked_location:
    if st.button(f"✕ Clear selection: {st.session_state.clicked_location}"):
        st.session_state.clicked_location = None
        st.rerun()

st.markdown("---")

# ── MAP ──────────────────────────────────────────────────────

st.subheader("📍 Where — Conflict Events Map")
st.caption("Click any dot to filter all charts to that location.")

col_map, col_stats = st.columns([3, 1])

event_colors = {
    "Explosions/Remote violence": "#d62728",
    "Battles": "#ff7f0e",
    "Violence against civilians": "#9467bd",
    "Protests": "#2ca02c",
    "Riots": "#8c564b",
    "Strategic developments": "#888888"
}

with col_map:
    map_df = filtered.copy()
    map_df['color'] = map_df['event_type'].map(event_colors).fillna('#888888')
    map_df['size'] = (map_df['fatalities'] + 1) * 3

    fig_map = px.scatter_mapbox(
        map_df,
        lat='latitude',
        lon='longitude',
        color='event_type',
        color_discrete_map=event_colors,
        size='fatalities_size',
        size_max=30,
        hover_name='location',
        hover_data={
            'event_date': True,
            'event_type': True,
            'fatalities': True,
            'actor1': True,
            'latitude': False,
            'longitude': False,
            'fatalities_size': False
        },
        zoom=7,
        center={"lat": 33.8, "lon": 35.5},
        height=550,
        mapbox_style="carto-positron",
        opacity=0.7,
        title=""
    )

    fig_map.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title="Event type",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ddd",
            borderwidth=1
        )
    )

    clicked = st.plotly_chart(
        fig_map,
        use_container_width=True,
        on_select="rerun",
        key="map_chart"
    )

    if clicked and clicked.get("selection") and clicked["selection"].get("points"):
        point = clicked["selection"]["points"][0]
        loc = point.get("hovertext") or point.get("customdata", [None])[0]
        if loc and loc != st.session_state.clicked_location:
            st.session_state.clicked_location = loc
            st.rerun()

with col_stats:
    st.markdown("##### Location stats")
    if st.session_state.clicked_location:
        loc_data = filtered[
            filtered['location'] == st.session_state.clicked_location
        ]
        st.markdown(f"**{st.session_state.clicked_location}**")
        st.metric("Events", len(loc_data))
        st.metric("Fatalities", int(loc_data['fatalities'].sum()))
        st.metric("Region", loc_data['admin1'].iloc[0] if len(loc_data) > 0 else "—")

        st.markdown("**Event types:**")
        type_counts = loc_data['event_type'].value_counts()
        for etype, count in type_counts.items():
            color = event_colors.get(etype, '#888')
            st.markdown(
                f'<span style="color:{color}">■</span> {etype}: **{count}**',
                unsafe_allow_html=True
            )

        st.markdown("**Recent events:**")
        recent = loc_data.sort_values('event_date', ascending=False).head(3)
        for _, row in recent.iterrows():
            st.caption(
                f"{row['event_date'].strftime('%b %d, %Y')} — "
                f"{row['sub_event_type']} "
                f"({int(row['fatalities'])} fatalities)"
            )
    else:
        st.info("Click a dot on the map to see location details here.")

        st.markdown("**Top locations:**")
        top_locs = filtered.groupby('location').agg(
            events=('event_type', 'count'),
            fatalities=('fatalities', 'sum')
        ).sort_values('events', ascending=False).head(5)

        for loc, row in top_locs.iterrows():
            st.markdown(f"**{loc}** — {row['events']} events, {int(row['fatalities'])} fatalities")

st.markdown("---")

# ── TIMELINE ─────────────────────────────────────────────────

st.subheader("📅 When — Timeline of Events & Media Sentiment")

# Timeline always uses full filtered data, not location-specific
# Only the title and fatalities chart change on location click
tl_data = filtered.copy()  # full region/type/date filter, NOT location
monthly = tl_data.groupby(['year_month', 'event_type']).size().reset_index(name='count')

# Title changes to reflect location if selected
timeline_title = (
    f'Conflict events — {st.session_state.clicked_location}'
    if st.session_state.clicked_location
    else 'Conflict events by month (all locations)'
)

# If location selected, overlay it on the full chart
if st.session_state.clicked_location:
    # Show two stacked charts instead of side by side
    event_chart_all = alt.Chart(monthly).mark_bar(opacity=0.8).encode(
        x=alt.X('year_month:O',
                title='Month',
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q', title='Events (all locations)'),
        color=alt.Color('event_type:N',
                        scale=alt.Scale(
                            domain=list(event_colors.keys()),
                            range=list(event_colors.values())
                        ),
                        legend=None),
        tooltip=['year_month:O', 'event_type:N', 'count:Q']
    ).properties(
        title='All selected locations — event timeline',
        height=160
    )

    loc_monthly = display_data.groupby(
        ['year_month', 'event_type']
    ).size().reset_index(name='count')

    event_chart_loc = alt.Chart(loc_monthly).mark_bar(opacity=0.9).encode(
        x=alt.X('year_month:O',
                title='Month',
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q',
                title=f'Events ({st.session_state.clicked_location})'),
        color=alt.Color('event_type:N',
                        scale=alt.Scale(
                            domain=list(event_colors.keys()),
                            range=list(event_colors.values())
                        ),
                        legend=alt.Legend(title="Event type")),
        tooltip=['year_month:O', 'event_type:N', 'count:Q']
    ).properties(
        title=f'📍 {st.session_state.clicked_location} — event timeline',
        height=160
    )

    event_chart = alt.vconcat(
        event_chart_all,
        event_chart_loc
    ).resolve_scale(color='shared')

else:
    event_chart = alt.Chart(monthly).mark_bar().encode(
        x=alt.X('year_month:O',
                title='Month',
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q', title='Number of events'),
        color=alt.Color('event_type:N',
                        scale=alt.Scale(
                            domain=list(event_colors.keys()),
                            range=list(event_colors.values())
                        ),
                        legend=alt.Legend(title="Event type")),
        tooltip=['year_month:O', 'event_type:N', 'count:Q']
    ).properties(
        title='Conflict events by month — all locations',
        height=220
    )

# GDELT tone — always full range, never filtered by location
tone_chart = alt.Chart(gdelt_tone).mark_line(
    color='#d62728', strokeWidth=2
).encode(
    x=alt.X('date:T', title='Date'),
    y=alt.Y('tone:Q',
            title='Avg tone',
            scale=alt.Scale(domain=[-12, 2])),
    tooltip=[
        alt.Tooltip('date:T', title='Date'),
        alt.Tooltip('tone:Q', title='Tone', format='.2f')
    ]
).properties(
    title='Media sentiment tone — GDELT (updates every 15 min)',
    height=180
)

zero_line = alt.Chart(
    pd.DataFrame({'y': [0]})
).mark_rule(
    color='gray', strokeDash=[4, 4], opacity=0.5
).encode(y='y:Q')

vol_chart = alt.Chart(gdelt_vol).mark_area(
    color='#1f77b4',
    opacity=0.4,
    line={'color': '#1f77b4', 'strokeWidth': 1.5}
).encode(
    x=alt.X('date:T', title='Date'),
    y=alt.Y('volume:Q', title='Article volume'),
    tooltip=[
        alt.Tooltip('date:T', title='Date'),
        alt.Tooltip('volume:Q', title='Volume', format='.0f')
    ]
).properties(
    title='Media coverage volume — GDELT',
    height=180
)

st.altair_chart(event_chart, use_container_width=True)
st.altair_chart((tone_chart + zero_line), use_container_width=True)
st.altair_chart(vol_chart, use_container_width=True)

st.markdown("---")

# ── HEATMAP — always all regions for comparison ───────────────

st.subheader("🔥 Intensity — Region × Month Heatmap")
st.caption("Color intensity = number of conflict events. Darker = more events. Location click highlights the row.")

heat_data = filtered.groupby(
    ['admin1', 'year_month']
).size().reset_index(name='events')

base_heat = alt.Chart(heat_data).mark_rect(
    stroke='white', strokeWidth=0.5
).encode(
    x=alt.X('year_month:O',
            title='Month',
            axis=alt.Axis(labelAngle=-45)),
    y=alt.Y('admin1:N',
            title='Region',
            sort=alt.EncodingSortField('events', op='sum', order='descending')),
    color=alt.Color('events:Q',
                    scale=alt.Scale(scheme='reds'),
                    legend=alt.Legend(title="Events")),
    tooltip=['admin1:N', 'year_month:O', 'events:Q']
).properties(
    height=300,
    title='Conflict intensity by region and month'
)

# If location clicked, overlay text on its region row
if st.session_state.clicked_location:
    clicked_region = filtered[
        filtered['location'] == st.session_state.clicked_location
    ]['admin1'].iloc[0] if len(
        filtered[filtered['location'] == st.session_state.clicked_location]
    ) > 0 else None

    if clicked_region:
        region_outline = alt.Chart(
            heat_data[heat_data['admin1'] == clicked_region]
        ).mark_rect(
            stroke='#333',
            strokeWidth=2,
            fill='transparent'
        ).encode(
            x=alt.X('year_month:O'),
            y=alt.Y('admin1:N')
        )
        st.altair_chart(base_heat + region_outline, use_container_width=True)
    else:
        st.altair_chart(base_heat, use_container_width=True)
else:
    st.altair_chart(base_heat, use_container_width=True)

st.markdown("---")

# ── FATALITIES ────────────────────────────────────────────────

st.subheader("💔 Human Cost — Fatalities Over Time")

col_fat1, col_fat2 = st.columns(2)

with col_fat1:
    fat_monthly = filtered.groupby(
        'year_month'
    )['fatalities'].sum().reset_index()

    fat_chart = alt.Chart(fat_monthly).mark_bar(
        color='#d62728', opacity=0.8
    ).encode(
        x=alt.X('year_month:O',
                title='Month',
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('fatalities:Q', title='Fatalities'),
        tooltip=['year_month:O', 'fatalities:Q']
    ).properties(
        height=250,
        title='Monthly fatalities — all selected regions'
    )
    st.altair_chart(fat_chart, use_container_width=True)

with col_fat2:
    fat_region = filtered.groupby(
        'admin1'
    )['fatalities'].sum().reset_index().sort_values(
        'fatalities', ascending=False
    )

    fat_region_chart = alt.Chart(fat_region).mark_bar(
        color='#9467bd'
    ).encode(
        x=alt.X('fatalities:Q', title='Total fatalities'),
        y=alt.Y('admin1:N',
                sort='-x',
                title='Region'),
        tooltip=['admin1:N', 'fatalities:Q']
    ).properties(
        height=250,
        title='Total fatalities by region'
    )
    st.altair_chart(fat_region_chart, use_container_width=True)

st.markdown("---")
st.caption(
    "Sources: ACLED (acleddata.com) · GDELT (gdeltproject.org) · "
    "Built with Streamlit + Altair + Plotly · "
    "Conflict data updated weekly · Media sentiment updates every 15 minutes"
)