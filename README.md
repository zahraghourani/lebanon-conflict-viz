# 🌍 Middle East Conflict Visualization

**Bridging Physical & Digital Worlds: Visualizing the Middle East Conflict Through Spatial and Sentiment Data**

A Streamlit dashboard combining ACLED conflict event data, GDELT real-time media sentiment, and Reddit public opinion into a single spatially-navigable and temporally-linked visual narrative.

---

## 📁 Project Structure

```
middle-east-conflict-viz/
│
├── data/
│   ├── raw/                        # Downloaded source data (never edit)
│   │   ├── acled_middle_east.csv   # Combined ACLED all countries
│   │   ├── acled_lebanon.csv       # Per-country ACLED files
│   │   ├── acled_palestine.csv
│   │   ├── acled_syria.csv
│   │   ├── acled_yemen.csv
│   │   ├── acled_iraq.csv
│   │   ├── ... (one per country)
│   │   ├── reddit_posts_middle_east.csv
│   │   └── reddit_comments_middle_east.csv
│   │
│   └── processed/                  # Cleaned data ready for dashboard
│       ├── gdelt_tone.csv
│       └── gdelt_volume.csv
│
├── notebooks/
│   ├── fetch_acled_middle_east.py  # Step 1 — pull ACLED data
│   ├── fetch_gdelt_middle_east.py  # Step 2 — pull GDELT data
│   ├── fetch_reddit_middle_east.py # Step 3 — pull Reddit data
│   └── explore_acled.py            # Optional EDA notebook
│
├── viz/
│   └── dashboard.py                # Main Streamlit dashboard
│
├── .env                            # Your API credentials (never commit)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/zahraghourani/lebanon-conflict-viz.git
cd lebanon-conflict-viz
```

### 2. Create and activate virtual environment

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

### 4. Create your `.env` file

Create a file called `.env` in the root of the project with your ACLED credentials:

```
ACLED_EMAIL=your_registered_email@example.com
ACLED_PASSWORD=your_acled_password
```

> ⚠️ Never commit this file to GitHub. It's already in `.gitignore`.

---

## 📦 Data Collection

Run the three scripts **in order**. All data is saved to `data/raw/` and `data/processed/`.

---

### Step 1 — ACLED Conflict Events

**Script:** `notebooks/fetch_acled_middle_east.py`

**What it does:** Downloads verified conflict event data with GPS coordinates, event types, actors, and fatalities for 17 Middle East countries from Jan 2024 to Apr 2025.

**Countries covered:**
Lebanon, Occupied Palestine, Syria, Israel, Jordan, Yemen, Saudi Arabia, Iraq, Kuwait, Bahrain, Qatar, UAE, Oman, Egypt, Libya, Iran, Turkey

**Run it:**

```bash
python notebooks/fetch_acled_middle_east.py
```

**Expected output:**

- One CSV per country in `data/raw/` (e.g. `acled_lebanon.csv`)
- One combined file: `data/raw/acled_middle_east.csv`
- Takes ~5–10 minutes depending on Syria, Yemen, Iraq (most events)

**Expected summary:**

```
COMBINED DATASET — BROADER MIDDLE EAST
  Total events    : ~80,000–120,000
  Countries       : Syria, Yemen, Iraq, Lebanon, ...
  Total fatalities: ~50,000+
```

> **Requires:** ACLED account (free at acleddata.com). Add credentials to `.env`.

---

### Step 2 — GDELT Media Sentiment

**Script:** `notebooks/fetch_gdelt_middle_east.py`

**What it does:** Pulls real-time global media sentiment (tone) and coverage volume for Middle East conflict keywords from GDELT. Covers Jan 2024 → Apr 2025 in 5 chunks of 3 months each.

**Run it:**

```bash
python notebooks/fetch_gdelt_middle_east.py
```

**Expected output:**

- `data/processed/gdelt_tone.csv` — daily average media sentiment score
- `data/processed/gdelt_volume.csv` — daily article volume
- Takes ~10 minutes (has built-in delays to respect GDELT rate limits)

**Expected summary:**

```
✓ Tone  : ~400 data points, range 2024-01-01 → 2025-04-14
✓ Volume: ~400 data points
```

> **Requires:** Nothing — no API key needed. GDELT is free and open.

---

### Step 3 — Reddit Public Opinion

**Script:** `notebooks/fetch_reddit_middle_east.py`

**What it does:** Scrapes Reddit posts and comments about Middle East conflict from 13 subreddits using Pullpush.io (free Reddit archive, no API key needed). Covers Jan 2024 → Apr 2025.

**Subreddits targeted:**
`worldnews`, `news`, `geopolitics`, `MiddleEast`, `Palestine`, `Lebanon`, `Syria`, `Yemen`, `Iran`, `Iraq`, `IsraelPalestine`, `AskMiddleEast`, `ArabIsraeliConflict`

**Run it:**

```bash
python notebooks/fetch_reddit_middle_east.py
```

**Expected output:**

- `data/raw/reddit_posts_middle_east.csv`
- `data/raw/reddit_comments_middle_east.csv`
- Takes ~15–20 minutes

**Expected summary:**

```
  Posts    : ~5,000–15,000
  Comments : ~10,000–30,000
```

> **Requires:** Nothing — Pullpush.io is free with no authentication needed.

---

## 🚀 Running the Dashboard

Once data is collected, launch the Streamlit dashboard:

```bash
streamlit run viz/dashboard.py
```

Then open your browser at: **http://localhost:8501**

### Dashboard features:

- 🗺️ **Interactive map** — click any event dot to filter all charts to that location
- 📅 **Timeline** — stacked monthly events by type
- 📰 **GDELT sentiment** — real-time media tone line chart (updates every 15 min)
- 📊 **GDELT volume** — media coverage area chart
- 💔 **Fatalities** — monthly and by-region charts
- 🔵 **Connected dot plot** — fatalities vs events per region
- 🔽 **Sidebar filters** — country, region, event type, date range

---

## ☁️ Deploying to Streamlit Cloud

1. Push your code to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → connect your GitHub repo
4. Set **Main file path** to: `viz/dashboard.py`
5. Under **Advanced settings → Secrets**, add your environment variables:

```
ACLED_EMAIL = "your_email@example.com"
ACLED_PASSWORD = "your_password"
```

6. Click **Deploy**

> ⚠️ Make sure `data/processed/gdelt_tone.csv` and `data/processed/gdelt_volume.csv` are committed to the repo so the dashboard has data on first load. The ACLED CSV is too large — the dashboard fetches it live or you can use Git LFS.

---

## 📊 Data Sources

| Source                             | Data                             | Update Frequency | Cost                         |
| ---------------------------------- | -------------------------------- | ---------------- | ---------------------------- |
| [ACLED](https://acleddata.com)     | Conflict events, GPS, fatalities | Weekly           | Free (registration required) |
| [GDELT](https://gdeltproject.org)  | Media sentiment & volume         | Every 15 minutes | Free, no key                 |
| [Pullpush.io](https://pullpush.io) | Reddit posts & comments          | Archived         | Free, no key                 |

---

## 📋 Requirements

```
streamlit
pandas
altair
plotly
requests
python-dotenv
```

Install all at once:

```bash
pip install streamlit pandas altair plotly requests python-dotenv
```

---

## 🗂️ Key Design Decisions

- **"Occupied Palestine"** used consistently everywhere (ACLED stores it as "Palestine")
- **ACLED lag** (~1 week) is framed as a "hybrid temporal architecture" — GDELT provides real-time sentiment while ACLED provides verified ground truth
- **Light academic color theme** for professional presentation
- **Heatmap replaced** with connected dot plot (fatalities vs events per region) for clearer comparison

---

## 📅 Project Timeline

| Date      | Milestone                                                          |
| --------- | ------------------------------------------------------------------ |
| Apr 16    | Data collection complete, dashboard expanded to full Middle East   |
| Apr 17–20 | Literature review (5 papers), preprocessing notebook, report draft |
| Apr 21–25 | Polish dashboard, finalize report, prepare presentation            |
| Apr 26    | **Submit by 11:59pm**                                              |
| Apr 28    | **15-minute live demo presentation**                               |

---

## 👩‍💻 Author

Zahra Ghourani — American University of Beirut
