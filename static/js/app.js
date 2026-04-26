let sliderTimer = null;
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
  document.getElementById("inp-date-to").value   = opts.date_max;
  state.dateFrom = opts.date_min;
  state.dateTo   = opts.date_max;

  // Country drill-down select
  const drillSel = document.getElementById("country-drill");
  opts.countries.forEach((c) => {
    const o = document.createElement("option");
    o.value = o.textContent = c;
    drillSel.appendChild(o);
  });

  await loadPeriods();

  // Hide slider by default (show all checked)
  document.getElementById("btn-back").style.display     = "none";
  document.getElementById("country-drill").style.display = "none";
  document.getElementById("week-slider").style.display  = "none";
  document.getElementById("week-label").style.display   = "none";
  state.showAll = true;
  document.getElementById("show-all").checked = true;

  await refreshAll();
  await renderHeatmap();

  // ── EVENT LISTENERS ────────────────────────────────────────────────────────

  document.getElementById("btn-apply").addEventListener("click", applyFilters);
  document.getElementById("btn-clear").addEventListener("click", clearFilters);
  document.getElementById("btn-heatmap").addEventListener("click", () => setMapMode("heatmap"));
  document.getElementById("btn-detail").addEventListener("click",  () => setMapMode("detail"));
  document.getElementById("btn-back").addEventListener("click",    () => setMapMode("heatmap"));

  document.getElementById("show-all").addEventListener("change", async function () {
    state.showAll = this.checked;
    const sliderEl   = document.getElementById("week-slider");
    const weekLabelEl = document.getElementById("week-label");
    sliderEl.style.display    = state.showAll ? "none" : "inline-block";
    weekLabelEl.style.display = state.showAll ? "none" : "inline";
    if (state.mapMode === "heatmap") await renderHeatmap();
    else await renderDetailMap();
  });

  // Debounced slider
  document.getElementById("week-slider").addEventListener("input", function () {
    state.weekIdx = +this.value;
    document.getElementById("week-label").textContent = state.weeks[state.weekIdx] || "";
    clearTimeout(sliderTimer);
    sliderTimer = setTimeout(async () => {
      if (state.mapMode === "heatmap") await renderHeatmap();
      else await renderDetailMap();
    }, 150);
  });

  document.getElementById("btn-play").addEventListener("click",  startPlay);
  document.getElementById("btn-pause").addEventListener("click", stopPlay);
  document.getElementById("btn-reset").addEventListener("click", () => {
    stopPlay();
    state.weekIdx = 0;
    document.getElementById("week-slider").value = 0;
    document.getElementById("week-label").textContent = state.weeks[0] || "";
    if (state.mapMode === "heatmap") renderHeatmap();
    else renderDetailMap();
  });

  document.getElementById("country-drill").addEventListener("change", async function () {
    const val = this.value;
    if (val) {
      state.drillCountry = val;
      mapInitialized = false;
      await renderDetailMap();
    }
  });

  // Period toggle
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.period  = btn.dataset.period;
      state.weekIdx = 0;
      state.showAll = false;
      document.getElementById("show-all").checked = false;
      document.getElementById("week-slider").style.display  = "inline-block";
      document.getElementById("week-label").style.display   = "inline";
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
      document.getElementById("chart-timeline-type").style.display    = tab === "by-type"    ? "block" : "none";
      document.getElementById("chart-timeline-country").style.display = tab === "by-country" ? "block" : "none";
      setTimeout(() => refreshTimeline(), 80);
    });
  });
}

// ── DATA LOADING ──────────────────────────────────────────────────────────────

async function loadPeriods() {
  const data = await fetchJSON(`${API}/api/periods?${buildParams()}&period=${state.period}`);
  state.weeks = data.periods || [];
  const slider = document.getElementById("week-slider");
  slider.max   = Math.max(0, state.weeks.length - 1);
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
  Array.from(typeSel.options).forEach((o)    => (o.selected = false));
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

// ── MAP MODE ──────────────────────────────────────────────────────────────────

function setMapMode(mode) {
  mapInitialized = false;
  state.mapMode  = mode;
  document.getElementById("btn-heatmap").classList.toggle("active", mode === "heatmap");
  document.getElementById("btn-detail").classList.toggle("active",  mode === "detail");
  document.getElementById("btn-back").style.display          = mode === "detail" ? "inline-block" : "none";
  document.getElementById("country-drill").style.display     = mode === "detail" ? "inline-block" : "none";
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
  document.getElementById("week-slider").style.display  = "inline-block";
  document.getElementById("week-label").style.display   = "inline";
  document.getElementById("btn-play").style.display     = "none";
  document.getElementById("btn-pause").style.display    = "inline";
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
  document.getElementById("btn-play").style.display  = "inline";
  document.getElementById("btn-pause").style.display = "none";
}

// ── METRICS ───────────────────────────────────────────────────────────────────

async function refreshMetrics() {
  const data = await fetchJSON(`${API}/api/metrics?${buildParams()}`);
  setMetric("m-events",     "Events",      data.total_events?.toLocaleString());
  setMetric("m-fatalities", "Fatalities",  data.total_fatalities?.toLocaleString());
  setMetric("m-countries",  "Countries",   data.total_countries);
  setMetric("m-regions",    "Regions",     data.total_regions);
  setMetric("m-posts",      "Reddit posts",data.reddit_posts?.toLocaleString());
  document.getElementById("sidebar-live-stats").innerHTML = `
    <div><strong>Showing:</strong> ${data.total_events?.toLocaleString() ?? 0} events</div>
    <div><strong>Fatalities:</strong> ${data.total_fatalities?.toLocaleString() ?? 0}</div>`;

  const activeFilters = (state.countries.length > 0 ? 1 : 0) + (state.eventTypes.length > 0 ? 1 : 0);
  const clearBtn = document.getElementById("btn-clear");
  if (activeFilters > 0) {
    clearBtn.textContent       = `✕ Clear Filters (${activeFilters} active)`;
    clearBtn.style.color       = "#ff9999";
    clearBtn.style.borderColor = "#ff9999";
  } else {
    clearBtn.textContent       = "✕ Clear Filters";
    clearBtn.style.color       = "#666";
    clearBtn.style.borderColor = "#2d2d4e";
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
  el.innerHTML = "<strong>Top locations by fatalities:</strong><br><br>" +
    (data.data || []).map((d) =>
      `<div style="margin-bottom:8px">
        <strong>${d.location}</strong><br>
        <small style="color:#666">${d.events} events · ${d.fatalities} fatalities</small>
      </div>`
    ).join("");
}

// ── TIMELINE ──────────────────────────────────────────────────────────────────

async function refreshTimeline() {
  const [typeData, countryData] = await Promise.all([
    fetchJSON(`${API}/api/timeline/events?${buildParams()}`),
    fetchJSON(`${API}/api/timeline/countries?${buildParams()}`),
  ]);

  const EVENT_COLORS_VEGA = {
    "Explosions/Remote violence": "#d62728",
    Battles: "#ff7f0e",
    "Violence against civilians": "#9467bd",
    Protests: "#2ca02c",
    Riots: "#8c564b",
    "Strategic developments": "#888888",
  };

  const annotations = [
  { month: "2024-04", label: "Iran missiles" , color: "#d62728" , fontweight: "bold" },
  { month: "2024-10", label: "Lebanon invasion" , color: "#ff7f0e", fontweight: "bold" },
  { month: "2024-11", label: "Ceasefire talks" , color: "#2ca02c" , fontweight: "bold" },
];

  const specType = {
  $schema: "https://vega.github.io/schema/vega-lite/v5.json",
  data: { values: typeData.data },
  resolve: { legend: { color: "independent" } },   // ← ADD THIS
  layer: [
    {
      mark: { type: "area", interpolate: "monotone" },
      encoding: {
        x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
        y: { field: "count", type: "quantitative", stack: "center", axis: { title: "Events (relative scale)", format: "~s" } },
        color: {
          field: "event_type", type: "nominal",
          scale: { domain: Object.keys(EVENT_COLORS_VEGA), range: Object.values(EVENT_COLORS_VEGA) },
          legend: { title: "Event type" },          // ← legend stays here
        },
        tooltip: [
          { field: "year_month", title: "Month" },
          { field: "event_type", title: "Type" },
          { field: "count", title: "Events" },
        ],
      },
    },
    {
      data: { values: annotations },
      mark: { type: "rule", color: "#333", strokeDash: [4, 3], strokeWidth: 1.5 },
      encoding: { x: { field: "month", type: "ordinal" } },
    },
    {
      data: { values: annotations },
      mark: { type: "text", angle: -90, align: "right", dx: -4, fontSize: 11, color: "#333" },
      encoding: {
        x: { field: "month", type: "ordinal" },
        y: { value: 20 },
        text: { field: "label" },
      },
    },
  ],
  title: "Conflict events by month",
  height: 260, width: "container",
};

  const specCountry = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: countryData.data },
    mark: { type: "line", point: true },
    encoding: {
      x: { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y: { field: "count",      type: "quantitative", title: "Events" },
      color: { field: "country", type: "nominal", legend: { title: "Country" } },
      tooltip: [
        { field: "year_month", title: "Month" },
        { field: "country",    title: "Country" },
        { field: "count",      title: "Events" },
      ],
    },
    title: "Events by country (top 6)",
    height: 240, width: "container",
  };

  vegaEmbed("#chart-timeline-type", specType, { actions: false });
  setTimeout(() => vegaEmbed("#chart-timeline-country", specCountry, { actions: false }), 100);
}

// ── FATALITIES ────────────────────────────────────────────────────────────────

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
    height: 220, width: "container",
  };

  const specCountry = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: byCountry.data },
    mark: { type: "bar", color: "#9467bd" },
    encoding: {
      x: { field: "fatalities", type: "quantitative" },
      y: { field: "country",    type: "nominal", sort: "-x", title: "Country" },
      tooltip: [{ field: "country" }, { field: "fatalities" }],
    },
    title: "Fatalities by country",
    height: 220, width: "container",
  };

  vegaEmbed("#chart-fat-monthly",  specMonthly,  { actions: false });
  vegaEmbed("#chart-fat-country",  specCountry,  { actions: false });
}

// ── DOT PLOT ──────────────────────────────────────────────────────────────────

async function refreshDotPlot() {
  const data = await fetchJSON(`${API}/api/dotplot?${buildParams()}`);
  const rows = data.data || [];
  const melted = [];
  rows.forEach((r) => {
    melted.push({ country: r.country, metric: "Events (normalized)",     value: r.events_norm,     events: r.events, fatalities: r.fatalities });
    melted.push({ country: r.country, metric: "Fatalities (normalized)", value: r.fatalities_norm, events: r.events, fatalities: r.fatalities });
  });
  const countryOrder = rows.map((r) => r.country);

  const lines = {
    data: { values: rows },
    mark: { type: "rule", color: "#ccc", strokeWidth: 1.5 },
    encoding: {
      x:  { field: "events_norm",     type: "quantitative" },
      x2: { field: "fatalities_norm" },
      y:  { field: "country", type: "nominal", sort: countryOrder },
    },
  };
  const dots = {
    data: { values: melted },
    mark: { type: "point", size: 100, filled: true },
    encoding: {
      x: { field: "value",   type: "quantitative", title: "Normalized score (0–100)" },
      y: { field: "country", type: "nominal", sort: countryOrder, title: "Country" },
      color: {
        field: "metric", type: "nominal",
        scale: { domain: ["Events (normalized)", "Fatalities (normalized)"], range: ["#1f77b4", "#d62728"] },
        legend: { title: "Metric" },
      },
      tooltip: [
        { field: "country" },
        { field: "events",     title: "Total events" },
        { field: "fatalities", title: "Total fatalities" },
        { field: "value",      title: "Normalized", format: ".1f" },
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

// ── CONNECTED SCATTERPLOT ─────────────────────────────────────────────────────

// async function refreshConnectedScatter() {
//   try {
//         const data = await fetchJSON(`${API}/api/connected-scatter?${buildParams()}`);
//         console.log("Connected scatter data:", data);
//         const rows = data.data || [];
//         if (rows.length === 0) {
//             console.warn("No data for connected scatter");
//             document.getElementById("chart-connected-scatter").innerHTML = 
//                 '<p style="padding:20px;color:#666">No data available for current filters.</p>';
//             return;
//         }


//     const spec = {
//       $schema: "https://vega.github.io/schema/vega-lite/v5.json",
//       data: { values: rows },
//       layer: [
//         // Connecting line — temporal path
//         {
//           mark: { type: "line", color: "#aaa", strokeWidth: 1.5, opacity: 0.6 },
//           encoding: {
//             x: { field: "events",        type: "quantitative" },
//             y: { field: "avg_sentiment", type: "quantitative" },
//             order: { field: "week_start", type: "temporal" },
//           },
//         },
//         // Points colored by time
//         {
//           mark: { type: "point", filled: true, size: 60, opacity: 0.85 },
//           encoding: {
//             x: {
//               field: "events", type: "quantitative",
//               title: "Weekly conflict events (ACLED)",
//               scale: { zero: false },
//             },
//             y: {
//               field: "avg_sentiment", type: "quantitative",
//               title: "Avg Reddit sentiment (VADER)",
//               scale: { domain: [-1, 1] },
//             },
//             color: {
//               field: "week_start", type: "temporal",
//               scale: { scheme: "redyellowblue", reverse: true },
//               legend: { title: "Time →", format: "%b %Y" },
//             },
//             tooltip: [
//               { field: "week_label",    title: "Week" },
//               { field: "events",        title: "ACLED events" },
//               { field: "fatalities",    title: "Fatalities" },
//               { field: "avg_sentiment", title: "Avg sentiment", format: ".3f" },
//               { field: "post_count",    title: "Reddit posts" },
//             ],
//           },
//         },
//         // Zero reference line
//         {
//           mark: { type: "rule", color: "#999", strokeDash: [4, 4], opacity: 0.5 },
//           encoding: { y: { datum: 0 } },
//         },
//       ],
//       title: {
//         text: "Conflict Intensity vs. Public Sentiment — Weekly Path",
//         subtitle: "Each point = one week · Color gradient = time (dark=early, light=recent) · Line shows temporal trajectory",
//       },
//       height: 320,
//       width: "container",
//     };

//     vegaEmbed("#chart-connected-scatter", spec, { actions: false });
//     } catch (e) {
//         console.error("Connected scatter error:", e);
//     }
// }

// ── CALENDAR HEATMAP ──────────────────────────────────────────────────────────

// async function refreshCalendarHeatmap() {
//   try {
//         const data = await fetchJSON(`${API}/api/calendar-heatmap?${buildParams()}`);
//         console.log("Connected scatter data:", data);
//         const rows = data.data || [];
//         if (rows.length === 0) {
//             console.warn("No data for connected scatter");
//             document.getElementById("chart-connected-scatter").innerHTML = 
//                 '<p style="padding:20px;color:#666">No data available for current filters.</p>';
//             return;
//         }

//     const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

//     const spec = {
//       $schema: "https://vega.github.io/schema/vega-lite/v5.json",
//       data: { values: rows },
//       mark: { type: "rect", stroke: "#fff", strokeWidth: 0.5, cornerRadius: 2 },
//       encoding: {
//         x: {
//           field: "week", type: "ordinal",
//           title: "Week",
//           axis: {
//             labelAngle: -90,
//             labelFontSize: 9,
//             labelOverlap: true,
//             tickCount: 12,
//           },
//         },
//         y: {
//           field: "weekday", type: "ordinal",
//           sort: DAY_ORDER,
//           title: "Day",
//           axis: { labelFontSize: 11 },
//         },
//         color: {
//           field: "fatalities", type: "quantitative",
//           scale: {
//             scheme: "reds",
//             domainMin: 0,
//           },
//           legend: { title: "Fatalities", gradientLength: 120 },
//         },
//         tooltip: [
//           { field: "date",         title: "Date" },
//           { field: "fatalities",   title: "Fatalities" },
//           { field: "events",       title: "Events" },
//           { field: "dominant_type",title: "Main type" },
//         ],
//       },
//       title: {
//         text: "Daily Conflict Fatalities — Calendar Heatmap",
//         subtitle: "Each cell = one day · Color intensity = total fatalities · White = no data",
//       },
//       height: 180,
//       width: "container",
//     };

//     vegaEmbed("#chart-calendar", spec, { actions: false });
//     } catch (e) {
//         console.error("Calendar heatmap error:", e);
//       }
// }
async function refreshCalendarHeatmap() {
    const container = document.getElementById("chart-calendar");
    try {
        const data = await fetchJSON(`${API}/api/calendar-heatmap?${buildParams()}`);
        const rows = data.data || [];
        
        if (rows.length === 0) {
            container.innerHTML = '<p style="padding:20px;color:#666">No data available.</p>';
            return;
        }

        const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
        const width = container.clientWidth || window.innerWidth - 350 || 800;

        // Pre-process: create a clean week_label field and numeric week_idx
        rows.forEach(r => {
            r.week_idx = +r.week_idx;  // Ensure numeric
        });

        // Get sorted unique week indices
        const sortedWeeks = [...new Set(rows.map(r => r.week_idx))].sort((a, b) => a - b);
        
        // Create label mapping for tooltip (not for axis labelExpr)
        const weekLabelMap = {};
        rows.forEach(r => {
            if (!weekLabelMap[r.week_idx]) {
                weekLabelMap[r.week_idx] = r.week_label;
            }
        });

        const spec = {
            $schema: "https://vega.github.io/schema/vega-lite/v5.json",
            data: { values: rows },
            mark: { type: "rect", stroke: "#fff", strokeWidth: 0.5 },
            encoding: {
                x: {
                    field: "week_idx",
                    type: "ordinal",
                    title: "Week",
                    sort: sortedWeeks,
                    axis: { 
                        labelAngle: -45, 
                        labelFontSize: 9,
                        tickCount: 12,
                        // Simple expression: just show the value, no let
                        labelExpr: "datum.value",  
                    },
                },
                y: {
                    field: "weekday",
                    type: "ordinal",
                    sort: DAY_ORDER,
                    title: "Day",
                    axis: { labelFontSize: 11 },
                },
                color: {
                    field: "fatalities",
                    type: "quantitative",
                    scale: { scheme: "reds", domainMin: 0 },
                    legend: { title: "Fatalities", gradientLength: 120 },
                },
                tooltip: [
                    { field: "week_label", title: "Week" },  // Shows "Jan 01"
                    { field: "date", title: "Date" },
                    { field: "fatalities", title: "Fatalities" },
                    { field: "events", title: "Events" },
                    { field: "dominant_type", title: "Main type" },
                ],
            },
            title: {
                text: "Daily Conflict Fatalities — Calendar Heatmap",
                subtitle: "Each cell = one day · Color intensity = total fatalities",
            },
            height: 180,
            width: width - 50,
        };

        await vegaEmbed("#chart-calendar", spec, { actions: false });
    } catch (e) {
        console.error("Calendar heatmap error:", e);
        container.innerHTML = `<p style="padding:20px;color:#d62728">Error: ${e.message}</p>`;
    }
}

// ── DUMBBELL PLOT ─────────────────────────────────────────────────────────────

async function refreshDumbbell() {
  try {
        const data = await fetchJSON(`${API}/api/dumbbell?${buildParams()}`);
        console.log("Connected scatter data:", data);
        const rows = data.data || [];
        if (rows.length === 0) {
            console.warn("No data for connected scatter");
            document.getElementById("chart-connected-scatter").innerHTML = 
                '<p style="padding:20px;color:#666">No data available for current filters.</p>';
            return;
        }

    const startDate = rows[0]?.start_date || "Start";
    const midDate   = rows[0]?.mid_date   || "Mid";
    const endDate   = rows[0]?.end_date   || "End";

    // Melt to long format for dots
    const melted = [];
    rows.forEach((r) => {
      melted.push({ country: r.country, period: startDate, events: r.events_start, change: r.change });
      melted.push({ country: r.country, period: endDate,   events: r.events_end,   change: r.change });
    });

    const countryOrder = rows.map((r) => r.country);

    const lines = {
      data: { values: rows },
      mark: { type: "rule", strokeWidth: 2 },
      encoding: {
        x:  { field: "events_start", type: "quantitative" },
        x2: { field: "events_end" },
        y:  { field: "country", type: "nominal", sort: countryOrder },
        color: {
          condition: { test: "datum.change > 0", value: "#d62728" },
          value: "#2ca02c",
        },
        opacity: { value: 0.6 },
      },
    };

    const dots = {
      data: { values: melted },
      mark: { type: "point", filled: true, size: 100 },
      encoding: {
        x: { field: "events",  type: "quantitative", title: "Number of events" },
        y: { field: "country", type: "nominal", sort: countryOrder, title: "Country" },
        color: {
          field: "period", type: "nominal",
          scale: {
            domain: [startDate, endDate],
            range:  ["#1f77b4", "#d62728"],
          },
          legend: { title: "Period" },
        },
        tooltip: [
          { field: "country", title: "Country" },
          { field: "period",  title: "Period" },
          { field: "events",  title: "Events" },
        ],
      },
    };

    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      layer: [lines, dots],
      title: {
        text: `Conflict Escalation by Country — ${startDate} vs ${endDate}`,
        subtitle: "Blue = first half · Red = second half · Red line = escalation · Green line = de-escalation",
      },
      height: Math.max(280, rows.length * 32),
      width: "container",
    };

    vegaEmbed("#chart-dumbbell", spec, { actions: false });
    } catch (e) {
        console.error("Dumbell error:", e);
      }
}

// async function refreshConnectedScatter() {
//     try {
//         const data = await fetchJSON(`${API}/api/connected-scatter?${buildParams()}`);
//         console.log("✓ Connected scatter API response:", data);
//         const rows = data.data || [];
//         console.log("✓ Rows count:", rows.length);
        
//         if (rows.length === 0) {
//             document.getElementById("chart-connected-scatter").innerHTML = 
//                 '<p style="padding:20px;color:#666">No data for connected scatter.</p>';
//             return;
//         }
        
//         const spec = { /* ... your spec ... */ };
//         console.log("✓ Rendering Vega spec");
//         await vegaEmbed("#chart-connected-scatter", spec, { actions: false });
//         console.log("✓ Rendered successfully");
//     } catch (e) {
//         console.error("✗ Connected scatter error:", e);
//         document.getElementById("chart-connected-scatter").innerHTML = 
//             `<p style="padding:20px;color:#d62728">Error: ${e.message}</p>`;
//     }
// }
async function refreshConnectedScatter() {
    const container = document.getElementById("chart-connected-scatter");
    try {
        const data = await fetchJSON(`${API}/api/connected-scatter?${buildParams()}`);
        console.log("Connected scatter raw data:", data);
        const rows = data.data || [];
        
        if (rows.length === 0) {
            container.innerHTML = '<p style="padding:20px;color:#666">No data available.</p>';
            return;
        }

        // Ensure numeric types
        rows.forEach(r => {
            r.events = +r.events;
            r.fatalities = +r.fatalities;
            r.avg_sentiment = +r.avg_sentiment;
            r.post_count = +r.post_count;
        });

        const width = container.clientWidth || container.offsetWidth || window.innerWidth - 350 || 800;
        console.log("Container width:", width);

        const spec = {
            $schema: "https://vega.github.io/schema/vega-lite/v5.json",
            data: { values: rows },
            mark: { type: "point", filled: true, size: 80, opacity: 0.9 },
            encoding: {
                x: { 
                    field: "events", 
                    type: "quantitative", 
                    title: "Weekly conflict events",
                    scale: { zero: false }
                },
                y: { 
                    field: "avg_sentiment", 
                    type: "quantitative", 
                    title: "Avg Reddit sentiment",
                    scale: { domain: [-1, 1] }
                },
                color: {
                    field: "week_start",
                    type: "ordinal",
                    scale: { scheme: "viridis" },
                    legend: { title: "Week" }
                },
                tooltip: [
                    { field: "week_start", title: "Week" },
                    { field: "events", title: "ACLED events", format: "," },
                    { field: "avg_sentiment", title: "Avg sentiment", format: ".3f" }
                ]
            },
            title: {
                text: "Conflict Intensity vs. Public Sentiment",
                subtitle: "Each point = one week",
            },
            height: 320,
            width: width - 50,
        };

        const result = await vegaEmbed("#chart-connected-scatter", spec, { actions: false });
        console.log("Vega embed result:", result);
    } catch (e) {
        console.error("Connected scatter error:", e);
        container.innerHTML = `<p style="padding:20px;color:#d62728">Error: ${e.message}</p>`;
    }
}

// ── SENTIMENT ─────────────────────────────────────────────────────────────────

async function refreshSentiment() {
  const data = await fetchJSON(`${API}/api/sentiment`);
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: data.data },
    layer: [
      { mark: { type: "rule", color: "gray", strokeDash: [4, 4], opacity: 0.4 }, encoding: { y: { datum: 0 } } },
      {
        mark: { type: "area", color: "#d62728", opacity: 0.1, interpolate: "monotone" },
        encoding: {
          x:  { field: "date", type: "temporal", title: "Date" },
          y:  { field: "sentiment_7d", type: "quantitative", scale: { domain: [-1, 1] } },
          y2: { datum: 0 },
        },
      },
      {
        mark: { type: "line", color: "#d62728", strokeWidth: 2.5, interpolate: "monotone" },
        encoding: {
          x: { field: "date",         type: "temporal", title: "Date" },
          y: { field: "sentiment_7d", type: "quantitative", title: "Sentiment (VADER 7-day avg)", scale: { domain: [-1, 1] } },
          tooltip: [
            { field: "date",         title: "Date", type: "temporal" },
            { field: "sentiment_7d", title: "7-day avg", format: ".3f" },
            { field: "post_count",   title: "Posts" },
          ],
        },
      },
    ],
    title: "Reddit Sentiment — VADER 7-day rolling average",
    height: 220, width: "container",
  };
  vegaEmbed("#chart-sentiment", spec, { actions: false });
}

// ── VOLUME ────────────────────────────────────────────────────────────────────

async function refreshVolume() {
  const data = await fetchJSON(`${API}/api/volume`);
  const melted = [];
  (data.data || []).forEach((d) => {
    melted.push({ year_month: d.year_month, type: "posts",    count: d.posts });
    melted.push({ year_month: d.year_month, type: "comments", count: d.comments });
  });
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: melted },
    mark: "bar",
    encoding: {
      x:       { field: "year_month", type: "ordinal", title: "Month", axis: { labelAngle: -45 } },
      y:       { field: "count",      type: "quantitative", title: "Count" },
      xOffset: { field: "type",       type: "nominal" },
      color: {
        field: "type", type: "nominal",
        scale: { domain: ["posts", "comments"], range: ["#1f77b4", "#aec7e8"] },
        legend: { title: "Type" },
      },
      tooltip: [{ field: "year_month" }, { field: "type" }, { field: "count" }],
    },
    title: "Reddit Discussion Volume by Month",
    height: 220, width: "container",
  };
  vegaEmbed("#chart-volume", spec, { actions: false });
}

// ── TOP POSTS ─────────────────────────────────────────────────────────────────

async function refreshTopPosts() {
  const data = await fetchJSON(`${API}/api/top-posts?${buildParams()}`);
  const tbody = document.getElementById("posts-tbody");
  tbody.innerHTML = (data.data || [])
    .map((d, i) => `
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
      </tr>`)
    .join("");
}

async function refreshFatalitiesByType() {
  const data = await fetchJSON(
    `${API}/api/fatalities/by-type?${buildParams()}`
  );
  const rows = data.data || [];
  if (rows.length === 0) return;

  const EVENT_COLORS_VEGA = {
    "Explosions/Remote violence": "#d62728",
    "Battles":                    "#ff7f0e",
    "Violence against civilians": "#9467bd",
    "Protests":                   "#2ca02c",
    "Riots":                      "#8c564b",
    "Strategic developments":     "#888888",
  };

  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: rows },
    mark: {
      type: "line",
      point: { filled: true, size: 40 },
      strokeWidth: 2.5,
      interpolate: "monotone",
    },
    encoding: {
      x: {
        field: "year_month",
        type: "ordinal",
        title: "Month",
        axis: { labelAngle: -45, labelFontSize: 10 },
      },
      y: {
        field: "fatalities",
        type: "quantitative",
        title: "Total fatalities",
        scale: { zero: true },
      },
      color: {
        field: "event_type",
        type: "nominal",
        scale: {
          domain: Object.keys(EVENT_COLORS_VEGA),
          range:  Object.values(EVENT_COLORS_VEGA),
        },
        legend: { title: "Event type", orient: "right" },
      },
      strokeDash: {
        field: "event_type",
        type: "nominal",
        scale: {
          domain: [
            "Explosions/Remote violence",
            "Battles",
            "Violence against civilians",
            "Protests",
            "Riots",
            "Strategic developments",
          ],
          range: [[1,0],[1,0],[4,2],[4,2],[2,2],[6,3]],
        },
        legend: null,
      },
      tooltip: [
        { field: "year_month", title: "Month" },
        { field: "event_type", title: "Event type" },
        { field: "fatalities", title: "Fatalities" },
      ],
    },
    title: {
      text: "Monthly Fatalities by Event Type",
      subtitle: "Explosions/Remote violence and Battles account for the vast majority of deaths",
    },
    height: 320,
    width: "container",
  };

  vegaEmbed("#chart-fatalities-by-type", spec, { actions: false });
}

async function refreshSmallMultiples() {
  const data = await fetchJSON(`${API}/api/timeline/all-countries?${buildParams()}`);
  const rows = data.data || [];
  if (!rows.length) return;

  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.json",
    data: { values: rows },
    width: "container",           // ← use full container width
    facet: {
      field: "country",
      type: "nominal",
      columns: 4,
      title: null
    },
    spec: {
      mark: { type: "area", opacity: 0.3, color: "#d62728" },
      encoding: {
        x: {
          field: "year_month",
          type: "ordinal",
          axis: { labelAngle: -45, tickCount: 4, labelFontSize: 8 }
        },
        y: {
          field: "count",
          type: "quantitative",
          axis: { title: null, labelFontSize: 8 }
        }
      },
      height: 90, 
    },
    resolve: { scale: { y: "independent" } },
    title: {
      text: "Conflict Events Over Time — All Countries",
      subtitle: "Small multiples · Each chart independently scaled"
    }
  };
  vegaEmbed("#chart-small-multiples", spec, { actions: false });
}

async function refreshSubredditSentiment() {
  const container = document.getElementById("chart-subreddit");
  if (!container) {
    console.error("chart-subreddit div not found in HTML");
    return;
  }
  try {
    const data = await fetchJSON(`${API}/api/subreddit-sentiment`);
    console.log("Subreddit data:", data);
    if (!data?.data?.length) {
      container.innerHTML = '<p style="color:#888;padding:12px">No subreddit data.</p>';
      return;
    }

    const w = container.offsetWidth || container.clientWidth || 700;

    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      data: { values: data.data },
      mark: { type: "bar", cornerRadiusEnd: 4 },
      encoding: {
        y: {
          field: "subreddit",
          type: "nominal",
          sort: { field: "avg_sentiment", order: "ascending" },
          title: "Subreddit",
          axis: { labelFontSize: 12 },
        },
        x: {
          field: "avg_sentiment",
          type: "quantitative",
          title: "Avg VADER sentiment",
          scale: { domain: [-1, 1] },
          axis: { gridDash: [3, 3] },
        },
        color: {
          condition: { test: "datum.avg_sentiment < 0", value: "#d62728" },
          value: "#2ca02c",
        },
        tooltip: [
          { field: "subreddit",     title: "Subreddit" },
          { field: "avg_sentiment", title: "Avg sentiment", format: ".3f" },
          { field: "post_count",    title: "Posts" },
        ],
      },
      title: {
        text: "Average VADER Sentiment by Subreddit",
        subtitle: "Red = net negative · Green = net positive",
      },
      height: 280,
      width: w - 40,
    };

    await vegaEmbed("#chart-subreddit", spec, { actions: false });
    console.log("Subreddit chart rendered successfully");
  } catch (e) {
    console.error("Subreddit sentiment error:", e);
    container.innerHTML = `<p style="color:#d62728;padding:12px">Error: ${e.message}</p>`;
  }
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
        refreshSmallMultiples(),
        // Delay chart renders that need a computed container width
        new Promise(r => setTimeout(() => refreshFatalitiesByType().then(r),  50)),
        new Promise(r => setTimeout(() => refreshCalendarHeatmap().then(r),  150)),
        new Promise(r => setTimeout(() => refreshDumbbell().then(r),          250)),
        new Promise(r => setTimeout(() => refreshSentiment().then(r),        150)),
        new Promise(r => setTimeout(() => refreshVolume().then(r),           150)),
        // new Promise(r => setTimeout(() => refreshSubredditSentiment().then(r), 200)),
        new Promise(r => setTimeout(() => refreshAdvancedCharts().then(r),   350)),
        new Promise(r => setTimeout(() => refreshSubredditSentiment().then(r), 400)),
    ]);
}

document.addEventListener("DOMContentLoaded", init);