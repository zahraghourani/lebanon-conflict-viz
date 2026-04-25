# all chart functions
import pandas as pd
import altair as alt
import plotly.express as px

# ── COLOR SCHEME ──────────────────────────────────────────────────────────────
# Edit these to change colors across all charts at once

EVENT_COLORS = {
    "Explosions/Remote violence": "#d62728",
    "Battles":                    "#ff7f0e",
    "Violence against civilians": "#9467bd",
    "Protests":                   "#2ca02c",
    "Riots":                      "#8c564b",
    "Strategic developments":     "#888888"
}

COUNTRY_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
]


# ── MAP ───────────────────────────────────────────────────────────────────────

def make_map(filtered: pd.DataFrame) -> px.scatter_mapbox:
    """
    Interactive Plotly map of all conflict events.
    Dot size = fatalities, color = event type.
    Click a dot to filter all charts to that location.
    Edit zoom and center here to change default map view.
    """
    fig = px.scatter_mapbox(
        filtered,
        lat='latitude',
        lon='longitude',
        color='event_type',
        color_discrete_map=EVENT_COLORS,
        size='fatalities_size',
        size_max=15,  # Further reduced for better clarity in dense areas
        hover_name='location',
        hover_data={
            'event_date':      True,
            'event_type':      True,
            'fatalities':      True,
            'actor1':          True,
            'country':         True,
            'latitude':        False,
            'longitude':       False,
            'fatalities_size': False
        },
        zoom=4,
        center={"lat": 29.0, "lon": 40.0},   # centered on Middle East
        height=560,
        mapbox_style="stamen-terrain",
        opacity=0.5,  # Further reduced opacity to better visualize point density
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title="Event type",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ddd",
            borderwidth=1
        )
    )
    return fig


# ── TIMELINE ──────────────────────────────────────────────────────────────────

def make_event_timeline(filtered: pd.DataFrame, location: str = None) -> alt.Chart:
    """
    Stacked bar chart — events by month, colored by event type.
    If location is selected, shows two charts stacked: all + selected location.
    Edit height values here to resize the charts.
    """
    monthly = (
        filtered
        .groupby(['year_month', 'event_type'])
        .size()
        .reset_index(name='count')
    )

    base = alt.Chart(monthly).mark_bar().encode(
        x=alt.X('year_month:O', title='Month', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q', title='Number of events'),
        color=alt.Color(
            'event_type:N',
            scale=alt.Scale(
                domain=list(EVENT_COLORS.keys()),
                range=list(EVENT_COLORS.values())
            ),
            legend=alt.Legend(title="Event type")
        ),
        tooltip=['year_month:O', 'event_type:N', 'count:Q']
    ).properties(
        title='Conflict events by month',
        height=220
    )
    return base


def make_country_timeline(filtered: pd.DataFrame) -> alt.Chart:
    """
    Line chart — events by month per country.
    Edit here to switch between line/bar or change which countries show.
    """
    monthly = (
        filtered
        .groupby(['year_month', 'country'])
        .size()
        .reset_index(name='count')
    )
    chart = alt.Chart(monthly).mark_line(point=True).encode(
        x=alt.X('year_month:O', title='Month', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q', title='Events'),
        color=alt.Color('country:N', legend=alt.Legend(title="Country")),
        tooltip=['year_month:O', 'country:N', 'count:Q']
    ).properties(
        title='Events by country over time',
        height=220
    )
    return chart


# ── CONNECTED DOT PLOT ────────────────────────────────────────────────────────

def make_dot_plot(filtered: pd.DataFrame) -> alt.Chart:
    """
    Connected dot plot — fatalities vs events per country.
    This replaces the old heatmap.
    Each country has two dots connected by a line showing the gap
    between event count and fatality count (normalized).
    Edit min_events to filter out low-activity countries.
    """
    agg = (
        filtered
        .groupby('country')
        .agg(
            events=('event_type', 'count'),
            fatalities=('fatalities', 'sum')
        )
        .reset_index()
    )

    # normalize to 0-100 scale so both metrics are comparable
    agg['events_norm']     = (agg['events']     / agg['events'].max()     * 100).round(1)
    agg['fatalities_norm'] = (agg['fatalities'] / agg['fatalities'].max() * 100).round(1)

    # only show countries with at least 10 events
    agg = agg[agg['events'] >= 10].sort_values('fatalities', ascending=False)

    # melt to long format for Altair
    melted = agg.melt(
        id_vars=['country', 'events', 'fatalities'],
        value_vars=['events_norm', 'fatalities_norm'],
        var_name='metric',
        value_name='normalized_value'
    )
    melted['metric'] = melted['metric'].map({
        'events_norm':     'Events (normalized)',
        'fatalities_norm': 'Fatalities (normalized)'
    })

    # connecting lines
    lines = alt.Chart(agg).mark_rule(color='#ccc', strokeWidth=1.5).encode(
        x=alt.X('events_norm:Q',     title=''),
        x2='fatalities_norm:Q',
        y=alt.Y('country:N', sort='-x', title='Country')
    )

    # dots
    dots = alt.Chart(melted).mark_point(size=80, filled=True).encode(
        x=alt.X('normalized_value:Q', title='Normalized score (0–100)'),
        y=alt.Y('country:N', sort='-x', title='Country'),
        color=alt.Color(
            'metric:N',
            scale=alt.Scale(
                domain=['Events (normalized)', 'Fatalities (normalized)'],
                range=['#1f77b4', '#d62728']
            ),
            legend=alt.Legend(title="Metric")
        ),
        tooltip=[
            alt.Tooltip('country:N',           title='Country'),
            alt.Tooltip('events:Q',            title='Total events'),
            alt.Tooltip('fatalities:Q',        title='Total fatalities'),
            alt.Tooltip('normalized_value:Q',  title='Normalized', format='.1f'),
        ]
    )

    return (lines + dots).properties(
        title='Events vs Fatalities by Country (normalized)',
        height=max(250, len(agg) * 30)
    )


# ── FATALITIES ────────────────────────────────────────────────────────────────

def make_fatalities_monthly(filtered: pd.DataFrame) -> alt.Chart:
    """Monthly fatalities bar chart."""
    fat_monthly = (
        filtered
        .groupby('year_month')['fatalities']
        .sum()
        .reset_index()
    )
    return alt.Chart(fat_monthly).mark_bar(color='#d62728', opacity=0.85).encode(
        x=alt.X('year_month:O', title='Month', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('fatalities:Q', title='Fatalities'),
        tooltip=['year_month:O', 'fatalities:Q']
    ).properties(height=250, title='Monthly fatalities')


def make_fatalities_by_country(filtered: pd.DataFrame) -> alt.Chart:
    """Horizontal bar — total fatalities per country."""
    fat_country = (
        filtered
        .groupby('country')['fatalities']
        .sum()
        .reset_index()
        .sort_values('fatalities', ascending=False)
    )
    return alt.Chart(fat_country).mark_bar(color='#9467bd').encode(
        x=alt.X('fatalities:Q', title='Total fatalities'),
        y=alt.Y('country:N', sort='-x', title='Country'),
        tooltip=['country:N', 'fatalities:Q']
    ).properties(height=250, title='Fatalities by country')


# ── REDDIT CHARTS ─────────────────────────────────────────────────────────────

def make_sentiment_chart(daily: pd.DataFrame) -> alt.Chart:
    """
    Reddit sentiment line chart — replaces GDELT tone.
    Shows 7-day rolling average sentiment from post titles.
    Edit color or smoothing window in sentiment.py.
    """
    zero = alt.Chart(
        pd.DataFrame({'y': [0]})
    ).mark_rule(color='gray', strokeDash=[4, 4], opacity=0.4).encode(y='y:Q')

    line = alt.Chart(daily).mark_line(
        color='#d62728', strokeWidth=2
    ).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('sentiment_7d:Q',
                title='Avg sentiment (7-day rolling)',
                scale=alt.Scale(domain=[-1, 1])),
        tooltip=[
            alt.Tooltip('date:T',           title='Date'),
            alt.Tooltip('sentiment_7d:Q',   title='Sentiment', format='.3f'),
            alt.Tooltip('post_count:Q',     title='Posts that day'),
        ]
    ).properties(
        title='Reddit public sentiment — 7-day rolling avg (TextBlob on post titles)',
        height=200
    )
    return zero + line


def make_volume_chart(monthly: pd.DataFrame) -> alt.Chart:
    """
    Reddit posts + comments volume by month — replaces GDELT volume.
    Edit here to show only posts or only comments.
    """
    melted = monthly.melt(
        id_vars='year_month',
        value_vars=['posts', 'comments'],
        var_name='type',
        value_name='count'
    )
    return alt.Chart(melted).mark_bar().encode(
        x=alt.X('year_month:O', title='Month', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count:Q', title='Count'),
        color=alt.Color(
            'type:N',
            scale=alt.Scale(
                domain=['posts', 'comments'],
                range=['#1f77b4', '#aec7e8']
            ),
            legend=alt.Legend(title="Type")
        ),
        tooltip=['year_month:O', 'type:N', 'count:Q']
    ).properties(
        title='Reddit discussion volume by month (posts + comments)',
        height=200
    )


def make_top_posts_table(posts: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Returns top N posts by score for display as a table.
    Edit n to show more or fewer posts.
    """
    cols = ['created_date', 'subreddit', 'title', 'score', 'num_comments', 'permalink']
    available = [c for c in cols if c in posts.columns]
    top = (
        posts[available]
        .sort_values('score', ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
    top.index += 1
    return top


def make_event_type_heatmap(filtered: pd.DataFrame) -> alt.Chart:
    """
    Heatmap showing event type frequency by country.
    Useful for identifying which event types are prevalent in each region.
    """
    heatmap_data = (
        filtered
        .groupby(['country', 'event_type'])
        .size()
        .reset_index(name='count')
    )
    
    return alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('event_type:N', title='Event Type'),
        y=alt.Y('country:N', title='Country'),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='reds'), title='Count'),
        tooltip=['country:N', 'event_type:N', 'count:Q']
    ).properties(
        title='Event Type Distribution by Country',
        width=600,
        height=max(300, len(filtered['country'].unique()) * 20)
    )


def make_fatality_intensity_scatter(filtered: pd.DataFrame) -> alt.Chart:
    """
    Scatter plot showing fatality intensity (fatalities per event) by country.
    Helps identify which regions have more lethal events on average.
    """
    intensity = (
        filtered
        .groupby('country')
        .agg(
            total_events=('event_type', 'count'),
            total_fatalities=('fatalities', 'sum')
        )
        .reset_index()
    )
    intensity['fatality_intensity'] = intensity['total_fatalities'] / intensity['total_events']
    intensity = intensity[intensity['total_events'] >= 10]  # Filter for significance
    
    return alt.Chart(intensity).mark_circle(size=200).encode(
        x=alt.X('total_events:Q', title='Total Events', scale=alt.Scale(type='log')),
        y=alt.Y('fatality_intensity:Q', title='Avg Fatalities per Event'),
        color=alt.Color('total_fatalities:Q', scale=alt.Scale(scheme='oranges'), title='Total Fatalities'),
        tooltip=[
            alt.Tooltip('country:N', title='Country'),
            alt.Tooltip('total_events:Q', title='Total Events'),
            alt.Tooltip('total_fatalities:Q', title='Total Fatalities'),
            alt.Tooltip('fatality_intensity:Q', title='Avg Fatalities/Event', format='.2f')
        ]
    ).properties(
        title='Fatality Intensity by Country (Bubble size = Total Fatalities)',
        height=350
    )