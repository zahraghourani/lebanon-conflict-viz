# 🌍 Middle East Conflict Dashboard

**Bridging Physical & Digital Worlds: Visualizing the Middle East Conflict Through Spatial and Sentiment Data**

A full-stack interactive dashboard combining **ACLED** conflict event data and **Reddit** public opinion into a single spatially-navigable and temporally-linked visual narrative — powered by FastAPI, D3.js, Vega-Lite, and Plotly.

> **Course:** DSC 614 — Data Visualization · Spring 2026 · Lebanese American University  
> **Author:** Zahra Ghourani

---

## 📊 Visualization Inventory

### Core Visualizations

| Chart | Library | What it shows |
|---|---|---|
| 🗺️ **Bubble Map** (regional) | Plotly | Country-level event clusters, size = events, color = dominant type |
| 📍 **Event Scatter Map** (detail) | Plotly | Individual ACLED events with GPS coordinates |
| ▶️ **Animated Timeline** | Plotly | Step through conflict by day / week / month |
| 📅 **Stacked Bar Timeline** | Vega-Lite | Monthly events grouped by type or country |
| 💔 **Monthly Fatalities Bar** | Vega-Lite | Total deaths per month |
| 🌍 **Fatalities by Country** | Vega-Lite | Horizontal ranked bar |
| ⚖️ **Connected Dot Plot** | Vega-Lite | Events (blue) vs fatalities (red) per country — gap reveals lethality |
| 📊 **Fatalities by Event Type** | Vega-Lite | Stacked monthly breakdown by conflict category |
| 📆 **Calendar Heatmap** | Vega-Lite + D3 | Day × week grid, color = daily fatalities |
| 📈 **Dumbbell Plot** | D3.js | First-half vs second-half event counts per country |
| 🔗 **Connected Scatter** | Vega-Lite | Weekly events vs Reddit sentiment — temporal trajectory |
| 📰 **Volume Area Chart** | Vega-Lite | Daily global media coverage volume |

### 🔬 Advanced Visualizations *(new)*

| Chart | Technique | Literature Grounding |
|---|---|---|
| 🌐 **Zoomable Sunburst** | D3 `d3-hierarchy` / `d3-partition` | Stasko & Zhang (2000) *Focus+Context Radial Hierarchy*; Johnson & Shneiderman (1991) treemaps |
| 🔀 **Event-Type Co-occurrence Chord** | D3 `d3-chord` | CHORDination (ACM CHI 2024, arXiv:2408.02268); Krzywinski et al. (2009) Circos |
| 🌹 **Nightingale Coxcomb (Polar Area)** | D3 polar arcs, √-scale | Florence Nightingale (1858) *Diagram of the Causes of Mortality in the Army in the East*; Friendly (2008) *A Brief History of Data Visualization* |
| 📈 **Bump / Rank Chart** | D3 Catmull-Rom curves | Wilke (2019) *Fundamentals of Data Visualization* ch. 12; The Economist Olympic rankings style |

#### Why these charts?

**Sunburst** — Arms conflict data is inherently hierarchical (region → country → event type → actor). A zoomable sunburst lets analysts drill from the macro (which country produces the most events?) to the micro (what types of events within that country?) in a single interactive artifact. Unlike treemaps, the radial layout preserves angular proportions across zoom levels (Stasko & Zhang, 2000).

**Chord Diagram** — Standard bar charts cannot show *co-occurrence* relationships. The chord diagram reveals which conflict types habitually cluster together (e.g., do Battles always co-occur with Explosions in the same country-month?). This insight — derived from the ACM CHI 2024 CHORDination study on chord diagram perception — is analytically important for understanding conflict escalation dynamics.

**Nightingale Coxcomb** — The direct methodological ancestor of this visualization is Florence Nightingale's 1858 polar-area diagram, which used √-scaled radial areas to show British soldier mortality by cause and month. Applying the same technique to Middle East conflict fatalities by event type draws an explicit, historically resonant parallel: data visualization as a tool for humanitarian advocacy. The square-root radius scale (area ∝ fatalities) reduces skew from extreme monthly spikes.

**Bump Chart** — Bar charts show quantity; bump charts show *ordinal trajectory*. Seeing Syria drop from rank #1 to #3 while Yemen climbs communicates relative escalation in a way absolute counts obscure. Wilke (2019) identifies bump charts as optimal for "showing how rankings change over time" (ch. 12).

---

## 📁 Project Structure

```
middle-east-conflict-viz/
│
├── data/
│   ├── raw/                         # Downloaded source data (never edit)
│   │   ├── acled_middle_east.csv    # Combined ACLED all countries
│   │   ├── acled_lebanon.csv        # Per-country ACLED files
│   │   ├── acled_palestine.csv
│   │   ├── acled_syria.csv
│   │   ├── acled_yemen.csv
│   │   ├── acled_iraq.csv
│   │   ├── ...                      # one CSV per country
│   │   ├── reddit_posts_middle_east.csv
│   │   └── reddit_comments_middle_east.csv
│   │
│   └── processed/                   # Cleaned, dashboard-ready data
│       ├── acled_clean.csv          # Merged + cleaned ACLED
│       ├── reddit_posts_clean.csv   # Sentiment-annotated posts
│       └── reddit_comments_clean.csv
│
├── notebooks/
│   ├── fetch_acled_middle_east.py   # Step 1 — pull ACLED data
│   ├── fetch_reddit_middle_east.py  # Step 2 — pull Reddit data
│   └── explore_acled.py             # Optional EDA
│
├── static/
│   ├── css/
│   │   └── style.css                # Dark-mode dashboard styles
│   ├── js/
│   │   ├── app.js                   # State, routing, all chart refreshers
│   │   ├── filters.js               # Sidebar filter helpers
│   │   ├── map.js                   # Plotly map rendering
│   │   ├── charts.js                # Chart helper stubs
│   │   └── viz_advanced.js            # ★ 4 advanced D3 visualizations
│   └── favicon.png
│
├── index.html                       # Single-page dashboard shell
├── main.py                          # FastAPI backend (16 API endpoints)
├── .env                             # API credentials (never commit)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python · FastAPI · Pandas · VADER Sentiment |
| **Frontend** | Vanilla JS (ES2022) · D3.js v7 · Vega-Lite v5 · Plotly.js |
| **Maps** | Plotly `scattergeo` |
| **NLP** | VADER SentimentIntensityAnalyzer |
| **Data** | ACLED, Reddit (via Pullpush.io) |

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/zahraghourani/lebanon-conflict-viz.git
cd lebanon-conflict-viz
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt** (minimum):
```
fastapi
uvicorn
pandas
vaderSentiment
python-dotenv
requests
```

### 4. Create `.env`

```
ACLED_EMAIL=your_registered_email@example.com
ACLED_PASSWORD=your_acled_password
```

> ⚠️ Never commit this file. It is already in `.gitignore`.

---

## 📦 Data Collection

Run the three scripts **in order**. All outputs go to `data/raw/` and `data/processed/`.

### Step 1 — ACLED Conflict Events

**Script:** `notebooks/fetch_acled_middle_east.py`

Downloads verified conflict event data with GPS coordinates, event types, actors, and fatalities for 17 Middle East countries from **Jan 2024 → Apr 2025**.

**Countries:** Lebanon, Occupied Palestine, Syria, Jordan, Yemen, Saudi Arabia, Iraq, Kuwait, Bahrain, Qatar, UAE, Oman, Egypt, Libya, Iran, Turkey

```bash
python notebooks/fetch_acled_middle_east.py
```

Expected output:

```
COMBINED DATASET — BROADER MIDDLE EAST
  Total events    : ~80,000–120,000
  Countries       : 17
  Total fatalities: ~50,000+
```

> Requires: free ACLED account at acleddata.com. Add credentials to `.env`.

---

### Step 2 — Reddit Public Opinion

**Script:** `notebooks/fetch_reddit_middle_east.py`

Scrapes Reddit posts and comments from 13 subreddits using Pullpush.io (free Reddit archive, no API key).

**Subreddits:** `worldnews`, `news`, `geopolitics`, `MiddleEast`, `Palestine`, `Lebanon`, `Syria`, `Yemen`, `Iran`, `Iraq`, `IsraelPalestine`, `AskMiddleEast`, `ArabIsraeliConflict`

```bash
python notebooks/fetch_reddit_middle_east.py
```

Expected output:

```
  Posts    : ~5,000–15,000
  Comments : ~10,000–30,000
```

---

## 🚀 Running the Dashboard

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000**

### API Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/filters/options` | Available countries, event types, date range |
| GET | `/api/metrics` | KPI counts (events, fatalities, countries, …) |
| GET | `/api/map/bubbles` | Country-level aggregates for bubble map |
| GET | `/api/map/events` | Individual event rows with GPS |
| GET | `/api/timeline/events` | Monthly events by event type |
| GET | `/api/timeline/countries` | Monthly events by top-6 countries |
| GET | `/api/fatalities/monthly` | Monthly fatality totals |
| GET | `/api/fatalities/countries` | Fatalities by country |
| GET | `/api/fatalities/by-type` | Monthly fatalities × event type |
| GET | `/api/dotplot` | Normalized events vs fatalities per country |
| GET | `/api/dumbbell` | First-half vs second-half event counts |
| GET | `/api/connected-scatter` | Weekly events vs Reddit sentiment |
| GET | `/api/calendar-heatmap` | Daily fatalities (calendar layout) |
| GET | `/api/reddit/sentiment` | Daily average Reddit sentiment |
| GET | `/api/reddit/top-posts` | Top-10 posts by upvotes |
| GET | `/api/sunburst` ⭐ | Hierarchical Country → Event Type tree |
| GET | `/api/chord` ⭐ | Event-type co-occurrence matrix |
| GET | `/api/bump` ⭐ | Monthly country event-count rankings |

---

## ☁️ Deploying

### Render / Railway / Fly.io

```bash
# Dockerfile (minimal)
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Commit `data/processed/` so the dashboard has data on first boot (ACLED CSVs are large — use Git LFS or fetch at startup).

---

## 📊 Data Sources

| Source | Data | Update Frequency | Cost |
|---|---|---|---|
| [ACLED](https://acleddata.com) | Conflict events, GPS, fatalities | Weekly | Free (registration required) |
| [Pullpush.io](https://pullpush.io) | Reddit posts & comments | Archived | Free, no key |

---

## 📚 Key References

| Reference | Relevance |
|---|---|
| Nightingale, F. (1858). *Diagram of the Causes of Mortality in the Army in the East*. | Coxcomb / polar-area diagram — direct methodological ancestor |
| Friendly, M. (2008). A brief history of data visualization. *Handbook of Data Visualization*, 15–56. | Historical framework for all chart choices |
| Stasko, J. & Zhang, E. (2000). Focus+context display and navigation techniques for enhancing radial, space-filling hierarchy visualizations. *IEEE InfoVis*. | Sunburst zoom rationale |
| CHORDination (2024). Evaluating Visual Design Choices in Chord Diagrams. *ACM CHI 2024*. arXiv:2408.02268. | Chord diagram design + perception |
| Wilke, C. O. (2019). *Fundamentals of Data Visualization*. O'Reilly. | Bump chart rationale (ch. 12), general principles |
| Raleigh, C. et al. (2010). Introducing ACLED: An Armed Conflict Location and Event Dataset. *Journal of Peace Research*, 47(5). | Primary data source methodology |
| Boschee, E. et al. (2015). ICEWS Coded Event Data. *Harvard Dataverse*. | Context for event-data approaches |

---

## 📋 Full Requirements

```
fastapi
uvicorn[standard]
pandas
vaderSentiment
python-dotenv
requests
```

Install:

```bash
pip install fastapi uvicorn pandas vaderSentiment python-dotenv requests
```

---

## 👩‍💻 Author

**Zahra El Ghourani** — Lebanese American University  
DSC 614 · Data Visualization · Spring 2026