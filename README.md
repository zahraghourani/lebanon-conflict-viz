# 🌍 Middle East Conflict Dashboard

**Bridging Physical and Digital Worlds: Visualizing the Middle East Conflict Through Spatial, Temporal, and Sentiment Data**

An interactive web dashboard that combines 112,628 verified conflict events from ACLED with 23,708 Reddit posts and comments to create a unified visual narrative of the 2024–2025 Middle East conflict.

> **DSC 614 — Data Visualization · Lebanese American University · Spring 2026**  
> **Author:** Zahra El Ghourani · zahra.elghourani@lau.edu

---

## 📊 What the Dashboard Shows

Ten coordinated visualizations built around three analytical questions:

| # | Chart | Question answered |
|---|---|---|
| 1 | KPI metric cards | Overall scale of crisis |
| 2 | Animated bubble map | Where did violence happen? |
| 3 | Streamgraph timeline | When did it escalate? |
| 4 | Connected dot plot | Which countries have high deaths per event? |
| 5 | Fatalities by event type | What killed the most people? |
| 6 | Nightingale polar area | Monthly fatality composition |
| 7 | Dumbbell escalation chart | Which countries escalated most? |
| 8 | Chord co-occurrence diagram | Which conflict types cluster together? |
| 9 | Calendar heatmap | Daily and weekly fatality patterns |
| 10 | Reddit sentiment + volume + subreddit chart | How did the public react online? |

---

## 🗂️ Project Structure

```
middle-east-conflict-viz/
│
├── data/
│   └── processed/
│       ├── acled_clean.csv              # Cleaned ACLED conflict events
│       ├── reddit_posts_clean.csv       # Cleaned Reddit posts
│       └── reddit_comments_clean.csv   # Cleaned Reddit comments
│
├── static/
│   ├── css/
│   │   └── style.css                   # Dashboard styles
│   ├── js/
│   │   ├── app.js                      # Filter state, chart orchestration
│   │   ├── map.js                      # D3 animated bubble map
│   │   └── viz_advanced.js             # D3 polar area + chord diagram
│   └── index.html                      # Single-page frontend
│
├── main.py                             # FastAPI backend (16 endpoints)
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup and Running

### 1. Clone the repo

```bash
git clone https://github.com/zahraghourani/lebanon-conflict-viz.git
cd lebanon-conflict-viz
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your data files

Place the following files in `data/processed/`:

- `acled_clean.csv` — downloaded from [acleddata.com](https://acleddata.com) (free registration required)
- `reddit_posts_clean.csv` — collected via [Pullpush.io](https://pullpush.io)
- `reddit_comments_clean.csv` — collected via [Pullpush.io](https://pullpush.io)

### 5. Run the dashboard

```bash
uvicorn main:app --reload
```

Then open your browser at: **http://127.0.0.1:8000**

---

## 🔌 API Endpoints

The FastAPI backend exposes 16 REST endpoints:

| Endpoint | Description |
|---|---|
| `GET /api/filters/options` | Country, event type, and date range options |
| `GET /api/metrics` | KPI card values |
| `GET /api/periods` | Period list for the temporal slider |
| `GET /api/map/bubbles` | Aggregated country-level bubble data |
| `GET /api/map/events` | Individual event points for the detail view |
| `GET /api/timeline/events` | Monthly events by type (streamgraph) |
| `GET /api/timeline/countries` | Monthly events for top-6 countries |
| `GET /api/fatalities/by-type` | Monthly fatalities by event type |
| `GET /api/dotplot` | Normalized events and fatalities per country |
| `GET /api/dumbbell` | First-half vs. second-half event counts |
| `GET /api/chord` | Event-type co-occurrence matrix |
| `GET /api/sentiment` | Daily VADER scores with 7-day rolling mean |
| `GET /api/volume` | Monthly Reddit post and comment counts |
| `GET /api/subreddit-sentiment` | Average VADER score per subreddit |
| `GET /api/top-posts` | Top-10 Reddit posts by upvote score |
| `GET /api/top-locations` | Top-7 locations by fatality count |

---

## 📦 Data Sources

| Source | Data | Records | Cost |
|---|---|---|---|
| [ACLED](https://acleddata.com) | Conflict events, GPS, fatalities | 112,628 | Free (registration required) |
| [Pullpush.io](https://pullpush.io) | Reddit posts | 6,598 | Free, no key |
| [Pullpush.io](https://pullpush.io) | Reddit comments | 17,110 | Free, no key |

**Coverage:** 17 Middle Eastern countries · January 2024 to April 2025

**Subreddits collected:** `worldnews`, `Palestine`, `Lebanon`, `geopolitics`, `Syria`, `AskMiddleEast`, `news`, `MiddleEast`, `Yemen`, `Iraq`, `Iran`

---

## 🛠️ Tech Stack

**Backend**
- Python 3.11
- FastAPI + Uvicorn
- Pandas
- vaderSentiment

**Frontend**
- D3.js v7 — map, polar area chart, chord diagram, dumbbell chart, dot plot
- Vega-Lite v5 — streamgraph, timeline, calendar heatmap, subreddit chart
- Plotly.js — sentiment timeline, volume chart
- Vanilla HTML / CSS / JavaScript

---

## 📋 Requirements

```
fastapi
uvicorn
pandas
vaderSentiment
```

Install:

```bash
pip install fastapi uvicorn pandas vaderSentiment
```

---

## 📚 References

- Mayer, B. (2024). *From Exploratory to Explanatory Interactive Visualization of Spatio-Temporal Conflict Data* [PhD Dissertation]. Otto-von-Guericke-Universität Magdeburg.
- Munzner, T. (2014). *Visualization Analysis and Design*. CRC Press.
- Raleigh et al. (2010). Introducing ACLED. *Journal of Peace Research*, 47(5).
- Hutto & Gilbert (2014). VADER. *ICWSM*.
- Wang et al. (2024). CHORDination. *VINCI 2024*.
- Nightingale, F. (1858). *Notes on Matters Affecting the Health of the British Army*.

---

## 👩‍💻 Author

**Zahra El Ghourani**  
Department of Computer Science and Mathematics  
Lebanese American University, Beirut, Lebanon  
zahra.elghourani@lau.edu