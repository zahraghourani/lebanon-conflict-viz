# viz/app.py — Full Dash dashboard for Middle East Conflict Visualization
# Run with: python viz/app.py
# Then open: http://localhost:8050

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

EVENT_COLORS = {
    "Explosions/Remote violence": "#d62728",
    "Battles":                    "#ff7f0e",
    "Violence against civilians": "#9467bd",
    "Protests":                   "#2ca02c",
    "Riots":                      "#8c564b",
    "Strategic developments":     "#888888"
}

COUNTRY_CENTERS = {
    'Occupied Palestine': {'lat': 31.9,  'lon': 35.2,  'zoom': 7},
    'Lebanon':            {'lat': 33.9,  'lon': 35.5,  'zoom': 7},
    'Syria':              {'lat': 34.8,  'lon': 38.9,  'zoom': 6},
    'Yemen':              {'lat': 15.6,  'lon': 48.5,  'zoom': 6},
    'Iraq':               {'lat': 33.2,  'lon': 43.7,  'zoom': 6},
    'Iran':               {'lat': 32.4,  'lon': 53.7,  'zoom': 5},
    'Turkey':             {'lat': 38.9,  'lon': 35.2,  'zoom': 5},
    'Jordan':             {'lat': 30.6,  'lon': 36.5,  'zoom': 7},
    'Egypt':              {'lat': 26.8,  'lon': 30.8,  'zoom': 5},
    'Libya':              {'lat': 26.3,  'lon': 17.2,  'zoom': 5},
    'Saudi Arabia':       {'lat': 23.9,  'lon': 45.1,  'zoom': 5},
    'Kuwait':             {'lat': 29.3,  'lon': 47.7,  'zoom': 8},
    'Bahrain':            {'lat': 26.0,  'lon': 50.6,  'zoom': 9},
    'Qatar':              {'lat': 25.3,  'lon': 51.2,  'zoom': 9},
    'United Arab Emirates': {'lat': 23.4,'lon': 53.8,  'zoom': 7},
    'Oman':               {'lat': 21.5,  'lon': 55.9,  'zoom': 6},
}

# ── LOAD DATA ─────────────────────────────────────────────────────────────────

print("Loading data...")
acled = pd.read_csv("data/processed/acled_clean.csv", low_memory=False)
acled['event_date'] = pd.to_datetime(acled['event_date'])
acled['fatalities'] = pd.to_numeric(acled['fatalities'], errors='coerce').fillna(0).astype(int)
acled['fatalities_size'] = acled['fatalities'] + 1
acled['year_month'] = acled['event_date'].dt.strftime('%Y-%m')
if 'week' not in acled.columns:
    acled['week'] = acled['event_date'].dt.to_period('W').apply(
        lambda r: r.start_time.strftime('%b %d, %Y')
    )
print(f"ACLED: {len(acled):,} events")

posts = pd.read_csv("data/processed/reddit_posts_clean.csv")
posts['created_date'] = pd.to_datetime(posts['created_date'], errors='coerce')
posts['score'] = pd.to_numeric(posts['score'], errors='coerce').fillna(0)
posts['year_month'] = posts['created_date'].dt.strftime('%Y-%m')

comments = pd.read_csv("data/processed/reddit_comments_clean.csv")
comments['created_date'] = pd.to_datetime(comments['created_date'], errors='coerce')
comments['score'] = pd.to_numeric(comments['score'], errors='coerce').fillna(0)
comments['year_month'] = comments['created_date'].dt.strftime('%Y-%m')
print(f"Reddit: {len(posts):,} posts, {len(comments):,} comments")

# ── PRECOMPUTE VADER SENTIMENT ────────────────────────────────────────────────

print("Computing VADER sentiment (one-time)...")
analyzer = SentimentIntensityAnalyzer()

def vader_score(text):
    if not isinstance(text, str) or text.strip() == '':
        return 0.0
    return analyzer.polarity_scores(text)['compound']

posts['sentiment'] = posts['title'].apply(vader_score)
posts['weighted_sentiment'] = posts['sentiment'] * np.log1p(posts['score'].clip(lower=0))

comments['sentiment'] = comments['body'].apply(vader_score)
comments['weighted_sentiment'] = comments['sentiment'] * np.log1p(comments['score'].clip(lower=0))

# Daily sentiment (full data, pre-computed)
p_daily = posts[['created_date','sentiment','weighted_sentiment','score']].copy()
p_daily['source'] = 'post'
p_daily = p_daily.rename(columns={'created_date':'date'})

c_daily = comments[['created_date','sentiment','weighted_sentiment','score']].copy()
c_daily['source'] = 'comment'
c_daily = c_daily.rename(columns={'created_date':'date'})

combined_daily = pd.concat([p_daily, c_daily], ignore_index=True)
combined_daily['date'] = pd.to_datetime(combined_daily['date']).dt.date

daily_sentiment = (
    combined_daily.groupby('date')
    .agg(avg_sentiment=('sentiment','mean'),
         post_count=('source', lambda x: (x=='post').sum()),
         comment_count=('source', lambda x: (x=='comment').sum()))
    .reset_index()
)
daily_sentiment['date'] = pd.to_datetime(daily_sentiment['date'])
daily_sentiment = daily_sentiment.sort_values('date')
daily_sentiment['sentiment_7d'] = daily_sentiment['avg_sentiment'].rolling(7, min_periods=1).mean()
print("Sentiment done.")

# ── FILTER HELPERS ────────────────────────────────────────────────────────────

all_countries  = sorted(acled['country'].dropna().unique())
all_event_types = sorted(acled['event_type'].dropna().unique())
date_min = acled['event_date'].min().date()
date_max = acled['event_date'].max().date()
all_weeks = sorted(acled['week'].dropna().unique())

# ── APP INIT ──────────────────────────────────────────────────────────────────

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True
)
app.title = "Middle East Conflict Dashboard"

# ── LAYOUT ────────────────────────────────────────────────────────────────────

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "260px",
    "padding": "20px 16px",
    "background-color": "#f8f9fa",
    "overflow-y": "auto",
    "border-right": "1px solid #dee2e6",
    "z-index": 1000,
}

CONTENT_STYLE = {
    "margin-left": "270px",
    "padding": "20px 24px",
}

sidebar = html.Div([
    html.H5("🔎 Filters", className="mb-3 fw-bold"),

    html.Label("Country", className="fw-semibold small"),
    dcc.Dropdown(
        id='filter-country',
        options=[{'label': c, 'value': c} for c in all_countries],
        value=all_countries,
        multi=True,
        placeholder="Select countries...",
        className="mb-3"
    ),

    html.Label("Region", className="fw-semibold small"),
    dcc.Dropdown(
        id='filter-region',
        options=[],
        value=[],
        multi=True,
        placeholder="Select regions...",
        className="mb-3"
    ),

    html.Label("Event Type", className="fw-semibold small"),
    dcc.Dropdown(
        id='filter-event-type',
        options=[{'label': t, 'value': t} for t in all_event_types],
        value=all_event_types,
        multi=True,
        placeholder="Select event types...",
        className="mb-3"
    ),

    html.Label("Date Range", className="fw-semibold small"),
    dcc.DatePickerRange(
        id='filter-date',
        min_date_allowed=date_min,
        max_date_allowed=date_max,
        start_date=date_min,
        end_date=date_max,
        display_format='MMM DD, YYYY',
        className="mb-3",
        style={"font-size": "12px"}
    ),

    html.Hr(),

    html.Div(id='sidebar-stats', className="small text-muted"),

    html.Hr(),

    html.Small("💡 Use filters to explore. Charts update instantly.", className="text-muted"),

], style=SIDEBAR_STYLE)

content = html.Div([

    # ── HEADER ────────────────────────────────────────────────
    html.Div([
        html.H2("🌍 Middle East Conflict Dashboard", className="mb-1 fw-bold"),
        html.P(
            "ACLED verified conflict events · Reddit public sentiment (VADER NLP) · "
            "Jan 2024 – Apr 2025 · 17 countries · 112,000+ events",
            className="text-muted small mb-3"
        ),
    ]),

    # ── METRICS ───────────────────────────────────────────────
    html.Div(id='metrics-row', className="mb-3"),

    html.Hr(),

    # ── SECTION 1 — MAP ───────────────────────────────────────
    html.H4("📍 Where — Conflict Events Map", className="mb-1"),
    html.P("Heatmap shows conflict density. Select a country below to drill into city-level events.", className="text-muted small mb-2"),

    dbc.Row([
        dbc.Col([
            # Map mode toggle
            dbc.ButtonGroup([
                dbc.Button("🌡️ Heatmap", id='btn-heatmap', color="danger", size="sm", n_clicks=0),
                dbc.Button("🔍 Country Detail", id='btn-detail', color="outline-danger", size="sm", n_clicks=0),
            ], className="mb-2"),

            # Week controls
            dbc.Row([
                dbc.Col([
                    dbc.Button("▶ Play", id='btn-play', color="outline-secondary", size="sm"),
                ], width="auto"),
                dbc.Col([
                    dcc.Checklist(
                        id='check-all-weeks',
                        options=[{'label': ' Show full period', 'value': 'all'}],
                        value=['all'],
                        className="small mt-1"
                    ),
                ], width="auto"),
            ], className="mb-1 align-items-center g-2"),

            dcc.Slider(
                id='week-slider',
                min=0,
                max=len(all_weeks)-1,
                value=len(all_weeks)//2,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": True,
                         "transform": "weekLabel"},
                className="mb-2"
            ),

            html.Div(id='week-info', className="small text-muted mb-2"),

            # The map
            dcc.Graph(id='main-map', style={"height": "560px"},
                      config={"scrollZoom": True}),

            dcc.Interval(id='play-interval', interval=900, n_intervals=0, disabled=True),

        ], width=9),

        dbc.Col([
            html.H6("📊 Stats", className="fw-bold"),
            html.Label("Drill into country:", className="small fw-semibold"),
            dcc.Dropdown(
                id='country-drill',
                options=[{'label': c, 'value': c} for c in all_countries],
                placeholder="— select country —",
                className="mb-3",
                clearable=True
            ),
            html.Div(id='location-stats'),
        ], width=3),
    ]),

    html.Hr(),

    # ── SECTION 2 — TIMELINE ──────────────────────────────────
    html.H4("📅 When — Conflict Timeline", className="mb-2"),
    dbc.Tabs([
        dbc.Tab(dcc.Graph(id='chart-timeline-type'), label="By event type"),
        dbc.Tab(dcc.Graph(id='chart-timeline-country'), label="By country (top 6)"),
    ]),

    html.Hr(),

    # ── SECTION 3 — HUMAN COST ────────────────────────────────
    html.H4("💔 Human Cost — Fatalities & Intensity", className="mb-2"),
    dbc.Row([
        dbc.Col(dcc.Graph(id='chart-fat-monthly'), width=6),
        dbc.Col(dcc.Graph(id='chart-fat-country'), width=6),
    ]),

    html.P("Blue = events (normalized) · Red = fatalities (normalized) · Wide gap = high lethality",
           className="text-muted small"),
    dcc.Graph(id='chart-dot-plot'),

    html.Hr(),

    # ── SECTION 3B — GRID MAP ─────────────────────────────────
    html.H4("🗺️ Country Grid Map", className="mb-1"),
    html.P("Equal visual space for all countries regardless of geographic size.", className="text-muted small mb-2"),
    dbc.RadioItems(
        id='grid-metric',
        options=[
            {'label': '💔 Fatalities', 'value': 'fatalities'},
            {'label': '📍 Events',     'value': 'events'},
            {'label': '⚠️ Lethality',  'value': 'lethality'},
        ],
        value='fatalities',
        inline=True,
        className="mb-2"
    ),
    dcc.Graph(id='chart-grid-map', style={"height": "480px"}),

    html.Hr(),

    # ── SECTION 4 — REDDIT ────────────────────────────────────
    html.H4("💬 Public Voice — Reddit Sentiment & Discussion", className="mb-1"),
    html.P("VADER NLP on post titles and comment bodies · -1 = very negative · +1 = very positive",
           className="text-muted small mb-2"),

    html.H6("🔑 Key Finding — Ground Violence vs. Public Sentiment"),
    html.P("Gray bars = weekly conflict events · Red line = Reddit sentiment · When bars spike → sentiment drops",
           className="text-muted small"),
    dcc.Graph(id='chart-correlation'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='chart-sentiment'), width=6),
        dbc.Col(dcc.Graph(id='chart-volume'), width=6),
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id='chart-subreddit-sentiment'), width=6),
        dbc.Col(dcc.Graph(id='chart-keyword-sentiment'), width=6),
    ]),

    html.H6("Most Upvoted Reddit Posts", className="mt-3 mb-2"),
    html.Div(id='top-posts-table'),

    html.Hr(),

    # ── FOOTER ────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Small("📊 Conflict data: ACLED — acleddata.com", className="text-muted"), width=4),
        dbc.Col(html.Small("💬 Social data: Reddit via Pullpush.io", className="text-muted"), width=4),
        dbc.Col(html.Small("🔬 Sentiment: VADER NLP · Altair + Plotly + Dash", className="text-muted"), width=4),
    ]),

    # Hidden stores
    dcc.Store(id='store-map-mode', data='heatmap'),
    dcc.Store(id='store-filtered-json'),

], style=CONTENT_STYLE)

app.layout = html.Div([sidebar, content])

# ── CALLBACKS ─────────────────────────────────────────────────────────────────

# 1. Cascade region filter from country
@app.callback(
    Output('filter-region', 'options'),
    Output('filter-region', 'value'),
    Input('filter-country', 'value')
)
def update_regions(countries):
    if not countries:
        return [], []
    regions = sorted(acled[acled['country'].isin(countries)]['admin1'].dropna().unique())
    opts = [{'label': r, 'value': r} for r in regions]
    return opts, regions


# 2. Week slider label
@app.callback(
    Output('week-info', 'children'),
    Input('week-slider', 'value'),
    Input('check-all-weeks', 'value'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_week_info(week_idx, show_all, countries, regions, event_types, start, end):
    if show_all:
        return "📅 Full period selected"
    if not all_weeks or week_idx is None:
        return ""
    week = all_weeks[week_idx]
    df = apply_filters(countries, regions, event_types, start, end)
    wdf = df[df['week'] == week]
    return f"📅 Week of {week} · {len(wdf):,} events · {int(wdf['fatalities'].sum()):,} fatalities"


# 3. Map mode toggle
@app.callback(
    Output('store-map-mode', 'data'),
    Output('btn-heatmap', 'color'),
    Output('btn-detail', 'color'),
    Input('btn-heatmap', 'n_clicks'),
    Input('btn-detail', 'n_clicks'),
    State('store-map-mode', 'data'),
)
def toggle_map_mode(n1, n2, current):
    ctx = callback_context
    if not ctx.triggered:
        return 'heatmap', 'danger', 'outline-danger'
    btn = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn == 'btn-heatmap':
        return 'heatmap', 'danger', 'outline-danger'
    return 'detail', 'outline-danger', 'danger'


# 4. Play button controls interval
@app.callback(
    Output('play-interval', 'disabled'),
    Output('btn-play', 'children'),
    Input('btn-play', 'n_clicks'),
    State('play-interval', 'disabled'),
)
def toggle_play(n, is_disabled):
    if n:
        if is_disabled:
            return False, "⏸ Pause"
        return True, "▶ Play"
    return True, "▶ Play"


# 5. Auto-advance week slider
@app.callback(
    Output('week-slider', 'value'),
    Input('play-interval', 'n_intervals'),
    State('week-slider', 'value'),
)
def advance_week(n, current):
    if current is None:
        return 0
    return (current + 1) % len(all_weeks)


# ── FILTER HELPER ─────────────────────────────────────────────────────────────

def apply_filters(countries, regions, event_types, start, end):
    df = acled.copy()
    if countries:
        df = df[df['country'].isin(countries)]
    if regions:
        df = df[df['admin1'].isin(regions)]
    if event_types:
        df = df[df['event_type'].isin(event_types)]
    if start:
        df = df[df['event_date'] >= pd.Timestamp(start)]
    if end:
        df = df[df['event_date'] <= pd.Timestamp(end)]
    return df


# ── MAIN MAP ──────────────────────────────────────────────────────────────────

@app.callback(
    Output('main-map', 'figure'),
    Input('store-map-mode', 'data'),
    Input('week-slider', 'value'),
    Input('check-all-weeks', 'value'),
    Input('country-drill', 'value'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_map(mode, week_idx, show_all, drill_country,
               countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)

    selected_week = None if show_all else (all_weeks[week_idx] if week_idx is not None and all_weeks else None)

    # Country detail mode
    if mode == 'detail' and drill_country:
        ddf = df[df['country'] == drill_country].copy()
        if selected_week:
            wdf = ddf[ddf['week'] == selected_week]
            if not wdf.empty:
                ddf = wdf
        if len(ddf) > 3000:
            fat = ddf[ddf['fatalities'] > 0]
            noFat = ddf[ddf['fatalities'] == 0]
            ddf = pd.concat([
                fat.sample(min(len(fat), 2000), random_state=42),
                noFat.sample(min(len(noFat), 1000), random_state=42)
            ])
        ddf['date_str'] = ddf['event_date'].dt.strftime('%b %d, %Y')
        center = COUNTRY_CENTERS.get(drill_country, {'lat': 29, 'lon': 40, 'zoom': 6})
        fig = px.scatter_mapbox(
            ddf,
            lat='latitude', lon='longitude',
            color='event_type',
            color_discrete_map=EVENT_COLORS,
            size='fatalities_size',
            size_max=25,
            hover_name='location',
            custom_data=['date_str', 'event_type', 'fatalities', 'actor1'],
            zoom=center['zoom'],
            center={"lat": center['lat'], "lon": center['lon']},
            mapbox_style="carto-positron",
            opacity=0.8,
            height=560,
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "📅 %{customdata[0]}<br>"
                "⚡ %{customdata[1]}<br>"
                "💔 Fatalities: %{customdata[2]}<br>"
                "👤 %{customdata[3]}<br>"
                "<extra></extra>"
            )
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(title="Event type", bgcolor="rgba(255,255,255,0.9)",
                       bordercolor="#ddd", borderwidth=1, x=0, y=1),
            title=dict(text=f"{drill_country} — {selected_week or 'Full Period'}", x=0.5)
        )
        return fig

    # Heatmap mode (default)
    hdf = df.copy()
    if selected_week:
        wdf = hdf[hdf['week'] == selected_week]
        if not wdf.empty:
            hdf = wdf
    if len(hdf) > 5000:
        hdf = hdf.sample(5000, random_state=42)

    fig = px.density_mapbox(
        hdf,
        lat='latitude', lon='longitude',
        z='fatalities_size',
        radius=25,
        center={"lat": 29.0, "lon": 40.0},
        zoom=4,
        mapbox_style="carto-positron",
        color_continuous_scale=[
            [0.0, "#ffffcc"],
            [0.2, "#fed976"],
            [0.4, "#feb24c"],
            [0.6, "#fd8d3c"],
            [0.8, "#e31a1c"],
            [1.0, "#800026"],
        ],
        opacity=0.75,
        height=560,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        coloraxis_showscale=False,
        title=dict(
            text=f"Conflict Hotspots — {selected_week or 'Full Period'}",
            x=0.5, font=dict(size=13)
        )
    )
    return fig


# ── METRICS ───────────────────────────────────────────────────────────────────

@app.callback(
    Output('metrics-row', 'children'),
    Output('sidebar-stats', 'children'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_metrics(countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)
    n_events = len(df)
    n_fat = int(df['fatalities'].sum())
    n_countries = df['country'].nunique()
    n_regions = df['admin1'].nunique()

    metrics = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H4(f"{n_events:,}", className="mb-0 fw-bold"),
            html.Small("Events", className="text-muted")
        ])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H4(f"{n_fat:,}", className="mb-0 fw-bold text-danger"),
            html.Small("Fatalities", className="text-muted")
        ])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H4(str(n_countries), className="mb-0 fw-bold"),
            html.Small("Countries", className="text-muted")
        ])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H4(str(n_regions), className="mb-0 fw-bold"),
            html.Small("Regions", className="text-muted")
        ])]), width=2),
        dbc.Col(dbc.Card([dbc.CardBody([
            html.H4(f"{len(posts):,}", className="mb-0 fw-bold"),
            html.Small("Reddit posts", className="text-muted")
        ])]), width=2),
    ], className="g-2")

    sidebar_stats = [
        html.Strong(f"Showing: {n_events:,} events"),
        html.Br(),
        f"Fatalities: {n_fat:,}",
        html.Br(),
        f"Countries: {n_countries}",
        html.Br(),
        f"Regions: {n_regions}",
    ]
    return metrics, sidebar_stats


# ── LOCATION STATS ────────────────────────────────────────────────────────────

@app.callback(
    Output('location-stats', 'children'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
    Input('week-slider', 'value'),
    Input('check-all-weeks', 'value'),
    Input('country-drill', 'value'),
)
def update_location_stats(countries, regions, event_types, start, end,
                          week_idx, show_all, drill_country):
    df = apply_filters(countries, regions, event_types, start, end)
    selected_week = None if show_all else (all_weeks[week_idx] if week_idx is not None and all_weeks else None)

    if drill_country:
        cdf = df[df['country'] == drill_country]
        if selected_week:
            wdf = cdf[cdf['week'] == selected_week]
            if not wdf.empty:
                cdf = wdf
        type_counts = cdf['event_type'].value_counts()
        recent = cdf.sort_values('event_date', ascending=False).head(4)
        return html.Div([
            html.H6(drill_country, className="fw-bold mb-2"),
            html.P(f"Events: {len(cdf):,}", className="mb-1 small"),
            html.P(f"Fatalities: {int(cdf['fatalities'].sum()):,}", className="mb-2 small text-danger"),
            html.Strong("Event types:", className="small"),
            html.Ul([
                html.Li(
                    html.Span([
                        html.Span("■ ", style={"color": EVENT_COLORS.get(t, '#888')}),
                        f"{t}: {c}"
                    ], className="small")
                )
                for t, c in type_counts.items()
            ], className="ps-3 mb-2"),
            html.Strong("Recent:", className="small"),
            html.Ul([
                html.Li(
                    f"{row['event_date'].strftime('%b %d')} · {row['sub_event_type']} · {int(row['fatalities'])} fatalities · {row['location']}",
                    className="small"
                )
                for _, row in recent.iterrows()
            ], className="ps-3"),
        ])

    # Default: top locations
    top = (
        df.groupby('location')
        .agg(events=('event_type','count'), fatalities=('fatalities','sum'))
        .sort_values('fatalities', ascending=False)
        .head(6)
    )
    return html.Div([
        html.P("Top locations by fatalities:", className="small fw-bold mb-1"),
        html.Ul([
            html.Li(
                f"{loc} — {row['events']} events, {int(row['fatalities'])} fatalities",
                className="small"
            )
            for loc, row in top.iterrows()
        ], className="ps-3 small")
    ])


# ── TIMELINE CHARTS ───────────────────────────────────────────────────────────

@app.callback(
    Output('chart-timeline-type', 'figure'),
    Output('chart-timeline-country', 'figure'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_timelines(countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)

    # By event type
    monthly = df.groupby(['year_month','event_type']).size().reset_index(name='count')
    fig1 = px.bar(monthly, x='year_month', y='count', color='event_type',
                  color_discrete_map=EVENT_COLORS,
                  labels={'year_month':'Month','count':'Events','event_type':'Type'},
                  title='Conflict Events by Month',
                  height=300)
    fig1.update_layout(xaxis_tickangle=-45, legend_title='Event type',
                       plot_bgcolor='white', paper_bgcolor='white')

    # By country (top 6)
    top6 = df['country'].value_counts().head(6).index.tolist()
    df6 = df[df['country'].isin(top6)]
    monthly6 = df6.groupby(['year_month','country']).size().reset_index(name='count')
    fig2 = px.line(monthly6, x='year_month', y='count', color='country',
                   markers=True,
                   labels={'year_month':'Month','count':'Events'},
                   title='Events by Country (Top 6)',
                   height=300)
    fig2.update_layout(xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white')
    return fig1, fig2


# ── FATALITY CHARTS ───────────────────────────────────────────────────────────

@app.callback(
    Output('chart-fat-monthly', 'figure'),
    Output('chart-fat-country', 'figure'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_fatalities(countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)

    fat_m = df.groupby('year_month')['fatalities'].sum().reset_index()
    fig1 = px.bar(fat_m, x='year_month', y='fatalities',
                  color_discrete_sequence=['#d62728'],
                  labels={'year_month':'Month','fatalities':'Fatalities'},
                  title='Monthly Fatalities', height=280)
    fig1.update_traces(marker_color='#d62728')
    fig1.update_layout(xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white')

    fat_c = df.groupby('country')['fatalities'].sum().reset_index().sort_values('fatalities', ascending=True)
    fig2 = px.bar(fat_c, x='fatalities', y='country', orientation='h',
                  color_discrete_sequence=['#9467bd'],
                  labels={'fatalities':'Total Fatalities','country':'Country'},
                  title='Fatalities by Country', height=280)
    fig2.update_traces(marker_color='#9467bd')
    fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white')
    return fig1, fig2


# ── DOT PLOT ─────────────────────────────────────────────────────────────────

@app.callback(
    Output('chart-dot-plot', 'figure'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_dot_plot(countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)
    agg = df.groupby('country').agg(
        events=('event_type','count'),
        fatalities=('fatalities','sum')
    ).reset_index()
    agg = agg[agg['events'] >= 10].copy()
    if agg.empty:
        return go.Figure()
    agg['events_norm'] = (agg['events'] / agg['events'].max() * 100).round(1)
    agg['fatalities_norm'] = (agg['fatalities'] / max(agg['fatalities'].max(), 1) * 100).round(1)
    agg = agg.sort_values('fatalities', ascending=True)

    fig = go.Figure()
    for _, row in agg.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['events_norm'], row['fatalities_norm']],
            y=[row['country'], row['country']],
            mode='lines',
            line=dict(color='#ccc', width=2),
            showlegend=False,
            hoverinfo='skip'
        ))
    fig.add_trace(go.Scatter(
        x=agg['events_norm'], y=agg['country'],
        mode='markers',
        marker=dict(color='#1f77b4', size=12),
        name='Events (normalized)',
        customdata=agg[['events']],
        hovertemplate='%{y}<br>Events: %{customdata[0]:,}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=agg['fatalities_norm'], y=agg['country'],
        mode='markers',
        marker=dict(color='#d62728', size=12),
        name='Fatalities (normalized)',
        customdata=agg[['fatalities']],
        hovertemplate='%{y}<br>Fatalities: %{customdata[0]:,}<extra></extra>'
    ))
    fig.update_layout(
        title='Events vs Fatalities by Country (normalized 0–100)',
        xaxis_title='Normalized score (0–100)',
        yaxis_title='Country',
        height=max(350, len(agg)*40),
        plot_bgcolor='white', paper_bgcolor='white',
        legend=dict(orientation='h', y=1.05)
    )
    return fig


# ── GRID MAP ─────────────────────────────────────────────────────────────────

GRID_POSITIONS = {
    'Turkey':               (2, 0), 'Syria': (3, 1), 'Lebanon': (2, 1),
    'Occupied Palestine':   (2, 2), 'Jordan': (3, 2), 'Iraq': (4, 1),
    'Iran':                 (5, 1), 'Egypt': (1, 2), 'Libya': (0, 2),
    'Saudi Arabia':         (3, 3), 'Kuwait': (4, 2), 'Bahrain': (5, 2),
    'Qatar':                (5, 3), 'United Arab Emirates': (6, 3),
    'Oman':                 (6, 4), 'Yemen': (4, 4),
}
GRID_LABELS = {
    'Turkey':'TUR','Syria':'SYR','Lebanon':'LBN','Occupied Palestine':'PAL',
    'Jordan':'JOR','Iraq':'IRQ','Iran':'IRN','Egypt':'EGY','Libya':'LBY',
    'Saudi Arabia':'KSA','Kuwait':'KWT','Bahrain':'BHR','Qatar':'QAT',
    'United Arab Emirates':'UAE','Oman':'OMN','Yemen':'YEM',
}

@app.callback(
    Output('chart-grid-map', 'figure'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
    Input('grid-metric', 'value'),
)
def update_grid_map(countries, regions, event_types, start, end, metric):
    df = apply_filters(countries, regions, event_types, start, end)
    agg = df.groupby('country').agg(
        fatalities=('fatalities','sum'),
        events=('event_type','count')
    ).reset_index()
    agg['lethality'] = (agg['fatalities'] / agg['events'].replace(0,1)).round(2)
    if metric == 'lethality':
        agg.loc[agg['events'] < 50, 'lethality'] = 0

    grid = pd.DataFrame([
        {'country': k, 'col': v[0], 'row': v[1]}
        for k, v in GRID_POSITIONS.items()
    ])
    gdf = grid.merge(agg, on='country', how='left').fillna(0)
    gdf['label'] = gdf['country'].map(GRID_LABELS)
    gdf['value'] = gdf[metric]
    gdf['text'] = gdf.apply(
        lambda r: f"{r['label']}<br>{r['value']:,.0f}" if metric != 'lethality'
        else f"{r['label']}<br>{r['value']:.2f}", axis=1
    )

    color_scales = {'fatalities': 'Reds', 'events': 'Blues', 'lethality': 'Oranges'}
    titles = {'fatalities': 'Total Fatalities', 'events': 'Total Events', 'lethality': 'Fatalities per Event'}

    fig = px.scatter(
        gdf, x='col', y='row',
        color='value',
        color_continuous_scale=color_scales[metric],
        text='text',
        hover_data={'country': True, 'fatalities': True, 'events': True, 'lethality': ':.2f',
                    'col': False, 'row': False, 'value': False, 'label': False, 'text': False},
        title=f'Country Grid Map — {titles[metric]}',
        height=480,
    )
    fig.update_traces(
        marker=dict(size=60, symbol='square', line=dict(color='white', width=2)),
        textfont=dict(color='white', size=11),
        textposition='middle center',
    )
    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.5, 7.5]),
        yaxis=dict(visible=False, range=[-0.5, 5.5], autorange='reversed'),
        plot_bgcolor='white', paper_bgcolor='white',
        coloraxis_colorbar=dict(title=titles[metric])
    )
    return fig


# ── CORRELATION CHART ─────────────────────────────────────────────────────────

@app.callback(
    Output('chart-correlation', 'figure'),
    Input('filter-country', 'value'),
    Input('filter-region', 'value'),
    Input('filter-event-type', 'value'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_correlation(countries, regions, event_types, start, end):
    df = apply_filters(countries, regions, event_types, start, end)
    weekly = df.groupby('week').agg(
        events=('event_type','count'),
        fatalities=('fatalities','sum')
    ).reset_index().sort_values('week')

    # Weekly sentiment from full data
    p = posts[['created_date','sentiment']].copy()
    p['week'] = p['created_date'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%b %d, %Y'))
    c = comments[['created_date','sentiment']].copy()
    c['week'] = c['created_date'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%b %d, %Y'))
    ws = pd.concat([p,c]).groupby('week')['sentiment'].mean().reset_index(name='avg_sentiment')

    merged = weekly.merge(ws, on='week', how='left')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=merged['week'], y=merged['events'],
        name='Conflict Events',
        marker_color='rgba(150,150,150,0.6)',
        yaxis='y1'
    ))
    if merged['avg_sentiment'].notna().any():
        fig.add_trace(go.Scatter(
            x=merged['week'], y=merged['avg_sentiment'],
            name='Reddit Sentiment',
            line=dict(color='#d62728', width=2.5),
            mode='lines', yaxis='y2'
        ))
    fig.update_layout(
        title='Conflict Events vs. Public Sentiment Over Time',
        xaxis=dict(tickangle=-45, tickfont=dict(size=8)),
        yaxis=dict(title='Events', side='left'),
        yaxis2=dict(title='Avg Sentiment', side='right', overlaying='y', range=[-1,1]),
        legend=dict(x=0, y=1.1, orientation='h'),
        height=320,
        plot_bgcolor='white', paper_bgcolor='white',
        bargap=0.1
    )
    return fig


# ── SENTIMENT CHARTS ──────────────────────────────────────────────────────────

@app.callback(
    Output('chart-sentiment', 'figure'),
    Output('chart-volume', 'figure'),
    Output('chart-subreddit-sentiment', 'figure'),
    Output('chart-keyword-sentiment', 'figure'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_sentiment_charts(start, end):
    ds = daily_sentiment.copy()
    if start:
        ds = ds[ds['date'] >= pd.Timestamp(start)]
    if end:
        ds = ds[ds['date'] <= pd.Timestamp(end)]

    # Sentiment line
    fig_sent = go.Figure()
    fig_sent.add_hline(y=0, line_dash='dash', line_color='gray', opacity=0.5)
    if not ds.empty:
        fig_sent.add_trace(go.Scatter(
            x=ds['date'], y=ds['avg_sentiment'],
            mode='lines', line=dict(color='#d62728', width=1),
            opacity=0.3, name='Daily', showlegend=False
        ))
        fig_sent.add_trace(go.Scatter(
            x=ds['date'], y=ds['sentiment_7d'],
            mode='lines', line=dict(color='#d62728', width=2.5),
            name='7-day avg', fill='tozeroy',
            fillcolor='rgba(214,39,40,0.1)'
        ))
    fig_sent.update_layout(
        title='Reddit Sentiment — VADER 7-day Rolling Average',
        yaxis=dict(title='Sentiment', range=[-1,1]),
        xaxis_title='Date', height=260,
        plot_bgcolor='white', paper_bgcolor='white'
    )

    # Volume grouped bar
    fp = posts.copy()
    fc = comments.copy()
    if start:
        fp = fp[fp['created_date'] >= pd.Timestamp(start)]
        fc = fc[fc['created_date'] >= pd.Timestamp(end if end else '2099')]
    pm = fp.groupby('year_month').size().reset_index(name='count')
    pm['type'] = 'posts'
    cm = fc.groupby('year_month').size().reset_index(name='count')
    cm['type'] = 'comments'
    vol = pd.concat([pm, cm])
    fig_vol = px.bar(vol, x='year_month', y='count', color='type', barmode='group',
                     color_discrete_map={'posts':'#1f77b4','comments':'#aec7e8'},
                     labels={'year_month':'Month','count':'Count','type':'Type'},
                     title='Reddit Discussion Volume by Month', height=260)
    fig_vol.update_layout(xaxis_tickangle=-45, plot_bgcolor='white', paper_bgcolor='white')

    # Subreddit sentiment
    sub_sent = posts.groupby('subreddit').agg(
        avg_sentiment=('sentiment','mean'),
        post_count=('id','count')
    ).reset_index()
    sub_sent = sub_sent[sub_sent['post_count'] >= 10].sort_values('avg_sentiment')
    sub_sent['color'] = sub_sent['avg_sentiment'].apply(
        lambda x: '#d62728' if x < -0.05 else ('#2ca02c' if x > 0.05 else '#888888')
    )
    fig_sub = go.Figure(go.Bar(
        x=sub_sent['avg_sentiment'], y=sub_sent['subreddit'],
        orientation='h',
        marker_color=sub_sent['color'],
        customdata=sub_sent[['post_count']],
        hovertemplate='%{y}<br>Sentiment: %{x:.3f}<br>Posts: %{customdata[0]}<extra></extra>'
    ))
    fig_sub.update_layout(
        title='Average Sentiment by Subreddit',
        xaxis_title='Avg VADER Sentiment',
        height=300, plot_bgcolor='white', paper_bgcolor='white'
    )

    # Keyword sentiment
    kw_sent = posts.groupby('keyword').agg(
        avg_sentiment=('sentiment','mean'),
        post_count=('id','count')
    ).reset_index()
    kw_sent = kw_sent[kw_sent['post_count'] >= 5].sort_values('avg_sentiment').head(15)
    kw_sent['color'] = kw_sent['avg_sentiment'].apply(
        lambda x: '#d62728' if x < -0.05 else ('#2ca02c' if x > 0.05 else '#888888')
    )
    fig_kw = go.Figure(go.Bar(
        x=kw_sent['avg_sentiment'], y=kw_sent['keyword'],
        orientation='h',
        marker_color=kw_sent['color'],
        hovertemplate='%{y}<br>Sentiment: %{x:.3f}<extra></extra>'
    ))
    fig_kw.update_layout(
        title='Average Sentiment by Keyword',
        xaxis_title='Avg VADER Sentiment',
        height=400, plot_bgcolor='white', paper_bgcolor='white'
    )

    return fig_sent, fig_vol, fig_sub, fig_kw


# ── TOP POSTS TABLE ───────────────────────────────────────────────────────────

@app.callback(
    Output('top-posts-table', 'children'),
    Input('filter-date', 'start_date'),
    Input('filter-date', 'end_date'),
)
def update_top_posts(start, end):
    fp = posts.copy()
    if start:
        fp = fp[fp['created_date'] >= pd.Timestamp(start)]
    if end:
        fp = fp[fp['created_date'] <= pd.Timestamp(end)]
    top = fp.nlargest(10, 'score')[
        ['created_date','subreddit','title','score','num_comments','sentiment','permalink']
    ].copy()
    top['created_date'] = pd.to_datetime(top['created_date']).dt.strftime('%b %d, %Y')
    top['sentiment'] = top['sentiment'].round(3)
    top['title'] = top['title'].str[:80] + '...'

    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("Date"), html.Th("Subreddit"), html.Th("Title"),
            html.Th("Score"), html.Th("Comments"), html.Th("Sentiment"), html.Th("Link")
        ])),
        html.Tbody([
            html.Tr([
                html.Td(row['created_date']),
                html.Td(row['subreddit']),
                html.Td(row['title']),
                html.Td(f"{int(row['score']):,}"),
                html.Td(f"{int(row['num_comments']):,}"),
                html.Td(
                    html.Span(
                        f"{row['sentiment']:.3f}",
                        style={"color": "#d62728" if row['sentiment'] < -0.05
                               else "#2ca02c" if row['sentiment'] > 0.05
                               else "#888"}
                    )
                ),
                html.Td(html.A("View →", href=row['permalink'], target="_blank")),
            ])
            for _, row in top.iterrows()
        ])
    ], bordered=True, hover=True, responsive=True, size='sm', striped=True)


# ── RUN ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)