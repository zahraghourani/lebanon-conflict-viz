let sliderTimer = null;
// let mapInitialized = false;
const API = "";

const state = {
  countries: [],
  eventTypes: [],
  dateFrom: "",
  dateTo: "",
  weeks: [],
  weekIdx: 0,
  showAll: true,
  mapMode: "heatmap",
  drillCountry: null,
  playing: false,
  playInterval: null,
  period: "day",
};

function buildParams(extra = {}) {
  const p = new URLSearchParams();
  if (state.countries.length) p.set("countries", state.countries.join(","));
  if (state.eventTypes.length) p.set("event_types", state.eventTypes.join(","));
  if (state.dateFrom) p.set("date_from", state.dateFrom);
  if (state.dateTo) p.set("date_to", state.dateTo);
  if (!state.showAll && state.weeks.length && state.weekIdx >= 0) {
    p.set("period", state.period);
    p.set("period_value", state.weeks[state.weekIdx]);
  }
  Object.entries(extra).forEach(([k, v]) => p.set(k, v));
  return p.toString();
}

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Request failed: ${url}`);
  return r.json();
}

async function init() {
  const opts = await fetchJSON(`${API}/api/filters/options`);

  // Populate country select
  const countrySel = document.getElementById("sel-countries");
  opts.countries.forEach((c) => {
    const o = document.createElement("option");
    o.value = o.textContent = c;
    countrySel.appendChild(o);
  });

  // Populate event type select
  const typeSel = document.getElementById("sel-types");
  opts.event_types.forEach((t) => {
    const o = document.createElement("option");
    o.value = o.textContent = t;
    typeSel.appendChild(o);
  });

  // Date defaults
  document.getElementById("inp-date-from").value = opts.date_min;
  document.getElementById("inp-date-to").value = opts.date_max;
  state.dateFrom = opts.date_min;
  state.dateTo = opts.date_max;

  // Country drill-down select
  const drillSel = document.getElementById("country-drill");
  opts.countries.forEach((c) => {
    const o = document.createElement("option");
    o.value = o.textContent = c;
    drillSel.appendChild(o);
  });

  // Load periods and hide slider by default
  await loadPeriods();
  document.getElementById("btn-back").style.display = "none";
  document.getElementById("country-drill").style.display = "none";
  document.getElementById("week-slider").style.display = "none";
  document.getElementById("week-label").style.display = "none";
  state.showAll = true;
  document.getElementById("show-all").checked = true;

  await refreshAll();
  await renderHeatmap();

  // ── EVENT LISTENERS ────────────────────────────────────────────

  // Filter buttons
  document.getElementById("btn-apply").addEventListener("click", applyFilters);
  document.getElementById("btn-clear").addEventListener("click", clearFilters);

  // Map mode buttons
  document.getElementById("btn-heatmap").addEventListener("click", () => setMapMode("heatmap"));
  document.getElementById("btn-detail").addEventListener("click", () => setMapMode("detail"));
  document.getElementById("btn-back").addEventListener("click", () => setMapMode("heatmap"));

  // Show all checkbox
  document.getElementById("show-all").addEventListener("change", async function () {
    state.showAll = this.checked;
    const sliderEl = document.getElementById("week-slider");
    const weekLabelEl = document.getElementById("week-label");
    sliderEl.style.display = state.showAll ? "none" : "inline-block";
    weekLabelEl.style.display = state.showAll ? "none" : "inline";
    if (state.mapMode === "heatmap") await renderHeatmap();
    else await renderDetailMap();
  });

  // Week slider with debounce — label updates instantly, map waits 150ms
  document.getElementById("week-slider").addEventListener("input", function () {
    state.weekIdx = +this.value;
    document.getElementById("week-label").textContent = state.weeks[state.weekIdx] || "";
    clearTimeout(sliderTimer);
    sliderTimer = setTimeout(async () => {
      if (state.mapMode === "heatmap") await renderHeatmap();
      else await renderDetailMap();
    }, 150);
  });

  // Play / Pause / Reset
  document.getElementById("btn-play").addEventListener("click", startPlay);
  document.getElementById("btn-pause").addEventListener("click", stopPlay);
  document.getElementById("btn-reset").addEventListener("click", () => {
    stopPlay();
    state.weekIdx = 0;
    document.getElementById("week-slider").value = 0;
    document.getElementById("week-label").textContent = state.weeks[0] || "";
    if (state.mapMode === "heatmap") renderHeatmap();
    else renderDetailMap();
  });

  // Country drill-down
  document.getElementById("country-drill").addEventListener("change", async function () {
    const val = this.value;
    if (val) {
      state.drillCountry = val;
      mapInitialized = false;
      await renderDetailMap();
    }
  });

  // Period toggle buttons
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.period = btn.dataset.period;
      state.weekIdx = 0;
      state.showAll = false;
      document.getElementById("show-all").checked = false;
      document.getElementById("week-slider").style.display = "inline-block";
      document.getElementById("week-label").style.display = "inline";
      mapInitialized = false;
      await loadPeriods();
      if (state.mapMode === "heatmap") await renderHeatmap();
      else await renderDetailMap();
    });
  });

  // Timeline tabs
  document.querySelectorAll("#tab-timeline .tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll("#tab-timeline .tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const typeDiv = document.getElementById("chart-timeline-type");
      const countryDiv = document.getElementById("chart-timeline-country");
      if (tab === "by-type") {
        typeDiv.style.display = "block";
        countryDiv.style.display = "none";
      } else {
        typeDiv.style.display = "none";
        countryDiv.style.display = "block";
        refreshTimeline();
      }
    });
  });
}

// ── DATA LOADING ──────────────────────────────────────────────────────────────

async function loadWeeks() {
  const data = await fetchJSON(`${API}/api/weeks?${buildParams()}`);
  state.weeks = data.weeks || [];
  const slider = document.getElementById("week-slider");
  slider.max = Math.max(0, state.weeks.length - 1);
  slider.value = state.weekIdx;
  document.getElementById("week-label").textContent = state.weeks[state.weekIdx] || "";
}

async function loadPeriods() {
  const data = await fetchJSON(
    `${API}/api/periods?${buildParams()}&period=${state.period}`
  );
  state.weeks = data.periods || [];
  const slider = document.getElementById("week-slider");
  slider.max = Math.max(0, state.weeks.length - 1);
  slider.value = 0;
  state.weekIdx = 0;
  document.getElementById("week-label").textContent = state.weeks[0] || "";
  const periodName = { day: "days", week: "weeks", month: "months" }[state.period];
  const countEl = document.getElementById("period-count");
  if (countEl) countEl.textContent = `${state.weeks.length} ${periodName}`;
}

// ── FILTERS ───────────────────────────────────────────────────────────────────

async function applyFilters() {
  mapInitialized = false;
  const countrySel = document.getElementById("sel-countries");
  const typeSel    = document.getElementById("sel-types");
  state.countries  = Array.from(countrySel.selectedOptions).map((o) => o.value);
  state.eventTypes = Array.from(typeSel.selectedOptions).map((o) => o.value);
  state.dateFrom   = document.getElementById("inp-date-from").value;
  state.dateTo     = document.getElementById("inp-date-to").value;
  state.weekIdx    = 0;
  await loadPeriods();
  await refreshAll();
}

async function clearFilters() {
  mapInitialized = false;
  const countrySel = document.getElementById("sel-countries");
  const typeSel    = document.getElementById("sel-types");
  Array.from(countrySel.options).forEach((o) => (o.selected = false));
  Array.from(typeSel.options).forEach((o) => (o.selected = false));
  const opts = await fetchJSON("/api/filters/options");
  document.getElementById("inp-date-from").value = opts.date_min;
  document.getElementById("inp-date-to").value   = opts.date_max;
  state.countries  = [];
  state.eventTypes = [];
  state.dateFrom   = opts.date_min;
  state.dateTo     = opts.date_max;
  state.weekIdx    = 0;
  document.getElementById("week-slider").value = 0;
  document.getElementById("week-label").textContent = state.weeks[0] || "";
  await loadPeriods();
  await refreshAll();
}

async function refreshAll() {
  await Promise.all([
    refreshMetrics(),
    refreshMap(),
    refreshStats(),
    refreshTimeline(),
    refreshFatalities(),
    refreshDotPlot(),
    refreshSentiment(),
    refreshVolume(),
    refreshTopPosts(),
  ]);
}

// ── MAP MODE ──────────────────────────────────────────────────────────────────

function setMapMode(mode) {
  mapInitialized = false;
  state.mapMode = mode;
  document.getElementById("btn-heatmap").classList.toggle("active", mode === "heatmap");
  document.getElementById("btn-detail").classList.toggle("active", mode === "detail");
  document.getElementById("btn-back").style.display = mode === "detail" ? "inline-block" : "none";
  document.getElementById("country-drill").style.display = mode === "detail" ? "inline-block" : "none";
  if (mode === "heatmap") {
    state.drillCountry = null;
    document.getElementById("country-drill").value = "";
    renderHeatmap();
  }
}

// ── PLAY / PAUSE ──────────────────────────────────────────────────────────────

function startPlay() {
  if (state.playing) return;
  state.playing = true;
  state.showAll = false;
  document.getElementById("show-all").checked = false;
  document.getElementById("week-slider").style.display = "inline-block";
  document.getElementById("week-label").style.display = "inline";
  document.getElementById("btn-play").style.display = "none";
  document.getElementById("btn-pause").style.display = "inline";

  const speed = state.period === "day" ? 400 : state.period === "week" ? 900 : 1200;

  state.playInterval = setInterval(async () => {
    if (state.weekIdx < state.weeks.length - 1) {
      state.weekIdx++;
      document.getElementById("week-slider").value = state.weekIdx;
      document.getElementById("week-label").textContent = state.weeks[state.weekIdx];
      if (state.mapMode === "heatmap") await renderHeatmap();
      else await renderDetailMap();
    } else {
      stopPlay();
    }
  }, speed);
}

function stopPlay() {
  state.playing = false;
  clearInterval(state.playInterval);
  document.getElementById("btn-play").style.display = "inline";
  document.getElementById("btn-pause").style.display = "none";
}

// ── METRICS ───────────────────────────────────────────────────────────────────

async function refreshMetrics() {
  const data = await fetchJSON(`${API}/api/metrics?${buildParams()}`);
  setMetric("m-events", "Events", data.total_events?.toLocaleString());
  setMetric("m-fatalities", "Fatalities", data.total_fatalities?.toLocaleString());
  setMetric("m-countries", "Countries", data.total_countries);
  setMetric("m-regions", "Regions", data.total_regions);
  setMetric("m-posts", "Reddit posts", data.reddit_posts?.toLocaleString());
  document.getElementById("sidebar-live-stats").innerHTML = `
    <div><strong>Showing:</strong> ${data.total_events?.toLocaleString() ?? 0} events</div>
    <div><strong>Fatalities:</strong> ${data.total_fatalities?.toLocaleString() ?? 0}</div>
  `;

  // Update clear button
  const activeFilters =
    (state.countries.length  > 0 ? 1 : 0) +
    (state.eventTypes.length > 0 ? 1 : 0);
  const clearBtn = document.getElementById("btn-clear");
  if (activeFilters > 0) {
    clearBtn.textContent = `✕ Clear Filters (${activeFilters} active)`;
    clearBtn.style.color = "#ff9999";
    clearBtn.style.borderColor = "#ff9999";
  } else {
    clearBtn.textContent = "✕ Clear Filters";
    clearBtn.style.color = "#aaa";
    clearBtn.style.borderColor = "#555";
  }
}

function setMetric(id, label, value) {
  document.getElementById(id).innerHTML = `
    <div class="metric-label">${label}</div>
    <div class="metric-value">${value ?? "—"}</div>`;
}

// ── MAP + STATS ───────────────────────────────────────────────────────────────

async function refreshMap() {
  if (state.mapMode === "heatmap") await renderHeatmap();
  else await renderDetailMap();
}

async function refreshStats() {
  const data = await fetchJSON(`${API}/api/top-locations?${buildParams()}`);
  const el = document.getElementById("stats-content");
  el.innerHTML =
    "<strong>Top locations by fatalities:</strong><br><br>" +
    (data.data || [])
      .map(
        (d) =>
          `<div style="margin-bottom:8px">
            <strong>${d.location}</strong><br>
            <small style="color:#666">${d.events} events · ${d.fatalities} fatalities</small>
          </div>`
      )
      .join("");
}

// ── CHARTS ────────────────────────────────────────────────────────────────────

async function refreshTimeline() {
  const [typeData, countryData] = await Promise.all([
    fetchJSON(`${API}/api/timeline/events?${buildParams()}`),
    fetchJSON(`${API}/api/timeline/countries?${buildParams()}`),
  ]);

  const EVENT_COLORS = {
    "Explosions/Remote violence": "#d62728",
    Battles: "#ff7f0e",
    "Violence against civilians": "#9467bd",
    Protests: "#2ca02c",
    Riots: "#8c564b",
    "Strategic developments": "#888888",
  };

  const specType = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: typeData.data },
    mark: "bar",
    encoding: {
      x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y: { field: "count", type: "quantitative", title: "Events" },
      color: {
        field: "event_type",
        type: "nominal",
        scale: { domain: Object.keys(EVENT_COLORS), range: Object.values(EVENT_COLORS) },
        legend: { title: "Event type" },
      },
      tooltip: [
        { field: "year_month", title: "Month" },
        { field: "event_type", title: "Type" },
        { field: "count", title: "Events" },
      ],
    },
    title: "Conflict events by month",
    height: 240,
    width: "container",
  };

  const specCountry = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: countryData.data },
    mark: { type: "line", point: true },
    encoding: {
      x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y: { field: "count", type: "quantitative", title: "Events" },
      color: { field: "country", type: "nominal", legend: { title: "Country" } },
      tooltip: [
        { field: "year_month", title: "Month" },
        { field: "country", title: "Country" },
        { field: "count", title: "Events" },
      ],
    },
    title: "Events by country (top 6)",
    height: 240,
    width: "container",
  };

  vegaEmbed("#chart-timeline-type", specType, { actions: false });
  setTimeout(() => {
    vegaEmbed("#chart-timeline-country", specCountry, { actions: false });
  }, 100);
}

async function refreshFatalities() {
  const [monthly, byCountry] = await Promise.all([
    fetchJSON(`${API}/api/fatalities/monthly?${buildParams()}`),
    fetchJSON(`${API}/api/fatalities/countries?${buildParams()}`),
  ]);

  const specMonthly = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: monthly.data },
    mark: { type: "bar", color: "#d62728" },
    encoding: {
      x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y: { field: "fatalities", type: "quantitative", title: "Fatalities" },
      tooltip: [{ field: "year_month" }, { field: "fatalities" }],
    },
    title: "Monthly fatalities",
    height: 220,
    width: "container",
  };

  const specCountry = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: byCountry.data },
    mark: { type: "bar", color: "#9467bd" },
    encoding: {
      x: { field: "fatalities", type: "quantitative", title: "Total fatalities" },
      y: { field: "country", type: "nominal", sort: "-x", title: "Country" },
      tooltip: [{ field: "country" }, { field: "fatalities" }],
    },
    title: "Fatalities by country",
    height: 220,
    width: "container",
  };

  vegaEmbed("#chart-fat-monthly", specMonthly, { actions: false });
  vegaEmbed("#chart-fat-country", specCountry, { actions: false });
}

async function refreshDotPlot() {
  const data = await fetchJSON(`${API}/api/dotplot?${buildParams()}`);
  const rows = data.data || [];
  const melted = [];
  rows.forEach((r) => {
    melted.push({ country: r.country, metric: "Events (normalized)", value: r.events_norm, events: r.events, fatalities: r.fatalities });
    melted.push({ country: r.country, metric: "Fatalities (normalized)", value: r.fatalities_norm, events: r.events, fatalities: r.fatalities });
  });
  const countryOrder = rows.map((r) => r.country);
  const lines = {
    data: { values: rows },
    mark: { type: "rule", color: "#ccc", strokeWidth: 1.5 },
    encoding: {
      x: { field: "events_norm", type: "quantitative" },
      x2: { field: "fatalities_norm" },
      y: { field: "country", type: "nominal", sort: countryOrder },
    },
  };
  const dots = {
    data: { values: melted },
    mark: { type: "point", size: 100, filled: true },
    encoding: {
      x: { field: "value", type: "quantitative", title: "Normalized score (0–100)" },
      y: { field: "country", type: "nominal", sort: countryOrder, title: "Country" },
      color: {
        field: "metric",
        type: "nominal",
        scale: { domain: ["Events (normalized)", "Fatalities (normalized)"], range: ["#1f77b4", "#d62728"] },
        legend: { title: "Metric" },
      },
      tooltip: [
        { field: "country" },
        { field: "events", title: "Total events" },
        { field: "fatalities", title: "Total fatalities" },
        { field: "value", title: "Normalized", format: ".1f" },
      ],
    },
  };
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    layer: [lines, dots],
    title: "Events vs Fatalities by Country (normalized 0–100)",
    height: Math.max(300, rows.length * 35),
    width: "container",
  };
  vegaEmbed("#chart-dotplot", spec, { actions: false });
}

async function refreshSentiment() {
  const data = await fetchJSON(`${API}/api/sentiment`);
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: data.data },
    layer: [
      {
        mark: { type: "rule", color: "gray", strokeDash: [4, 4], opacity: 0.4 },
        encoding: { y: { datum: 0 } },
      },
      {
        mark: { type: "area", color: "#d62728", opacity: 0.1, interpolate: "monotone" },
        encoding: {
          x: { field: "date", type: "temporal", title: "Date" },
          y: { field: "sentiment_7d", type: "quantitative", scale: { domain: [-1, 1] } },
          y2: { datum: 0 },
        },
      },
      {
        mark: { type: "line", color: "#d62728", strokeWidth: 2.5, interpolate: "monotone" },
        encoding: {
          x: { field: "date", type: "temporal", title: "Date" },
          y: { field: "sentiment_7d", type: "quantitative", title: "Sentiment (VADER 7-day avg)", scale: { domain: [-1, 1] } },
          tooltip: [
            { field: "date", title: "Date", type: "temporal" },
            { field: "sentiment_7d", title: "7-day avg", format: ".3f" },
            { field: "post_count", title: "Posts" },
          ],
        },
      },
    ],
    title: "Reddit Sentiment — VADER 7-day rolling average",
    height: 220,
    width: "container",
  };
  vegaEmbed("#chart-sentiment", spec, { actions: false });
}

async function refreshVolume() {
  const data = await fetchJSON(`${API}/api/volume`);
  const melted = [];
  (data.data || []).forEach((d) => {
    melted.push({ year_month: d.year_month, type: "posts", count: d.posts });
    melted.push({ year_month: d.year_month, type: "comments", count: d.comments });
  });
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: melted },
    mark: "bar",
    encoding: {
      x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y: { field: "count", type: "quantitative", title: "Count" },
      xOffset: { field: "type", type: "nominal" },
      color: {
        field: "type",
        type: "nominal",
        scale: { domain: ["posts", "comments"], range: ["#1f77b4", "#aec7e8"] },
        legend: { title: "Type" },
      },
      tooltip: [{ field: "year_month" }, { field: "type" }, { field: "count" }],
    },
    title: "Reddit Discussion Volume by Month",
    height: 220,
    width: "container",
  };
  vegaEmbed("#chart-volume", spec, { actions: false });
}

async function refreshTopPosts() {
  const data = await fetchJSON(`${API}/api/top-posts?${buildParams()}`);
  const tbody = document.getElementById("posts-tbody");
  tbody.innerHTML = (data.data || [])
    .map(
      (d, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${d.created_date ?? ""}</td>
      <td>r/${d.subreddit ?? ""}</td>
      <td>${(d.title || "").substring(0, 80)}...</td>
      <td>${Number(d.score || 0).toLocaleString()} ▲</td>
      <td style="color:${d.sentiment < -0.05 ? "#d62728" : d.sentiment > 0.05 ? "#2ca02c" : "#888"}">
        ${Number(d.sentiment || 0).toFixed(3)}
      </td>
      <td><a href="${d.permalink || "#"}" target="_blank">View →</a></td>
    </tr>`
    )
    .join("");
}

function formatPeriodLabel(periodStr, periodType) {
    if (!periodStr) return "";
    
    if (periodType === "day") {
        return new Date(periodStr).toLocaleDateString("en-US", {
            month: "short", day: "numeric", year: "numeric"
        });  // "Jan 9, 2024"
    } else if (periodType === "week") {
        // Parse ISO week "2024-W02"
        const [y, w] = periodStr.split("-W");
        const monday = new Date(y, 0, 1 + (w - 1) * 7 - new Date(y, 0, 1).getDay() + 1);
        const sunday = new Date(monday);
        sunday.setDate(sunday.getDate() + 6);
        return `${monday.toLocaleDateString("en-US", {month:"short", day:"numeric"})} – ${sunday.toLocaleDateString("en-US", {month:"short", day:"numeric", year:"numeric"})}`;
    } else if (periodType === "month") {
        return new Date(periodStr + "-01").toLocaleDateString("en-US", {
            month: "long", year: "numeric"
        });  // "January 2024"
    }
    return periodStr;
}

// Update in slider input handler:
document.getElementById("week-label").textContent = formatPeriodLabel(
    state.weeks[state.weekIdx], state.period
);

document.addEventListener("DOMContentLoaded", init);