let mapInitialized = false;
let currentMapMode = null;

const EVENT_ORDER = [
  "Explosions/Remote violence",
  "Battles",
  "Violence against civilians",
  "Protests",
  "Riots",
  "Strategic developments",
];

const EVENT_COLORS = {
  "Explosions/Remote violence": "#d62728",
  "Battles":                    "#ff7f0e",
  "Violence against civilians": "#9467bd",
  "Protests":                   "#2ca02c",
  "Riots":                      "#8c564b",
  "Strategic developments":     "#888888",
};

const COUNTRY_CENTERS = {
  "Occupied Palestine":   { lat: 31.9, lon: 35.2, zoom: 8 },
  "Lebanon":              { lat: 33.9, lon: 35.5, zoom: 8 },
  "Syria":                { lat: 34.8, lon: 38.9, zoom: 6 },
  "Yemen":                { lat: 15.6, lon: 48.5, zoom: 6 },
  "Iraq":                 { lat: 33.2, lon: 43.7, zoom: 6 },
  "Iran":                 { lat: 32.4, lon: 53.7, zoom: 5 },
  "Turkey":               { lat: 38.9, lon: 35.2, zoom: 5 },
  "Jordan":               { lat: 30.6, lon: 36.5, zoom: 7 },
  "Egypt":                { lat: 26.8, lon: 30.8, zoom: 5 },
  "Libya":                { lat: 26.3, lon: 17.2, zoom: 5 },
  "Saudi Arabia":         { lat: 23.9, lon: 45.1, zoom: 5 },
  "Kuwait":               { lat: 29.3, lon: 47.7, zoom: 8 },
  "Bahrain":              { lat: 26.0, lon: 50.6, zoom: 9 },
  "Qatar":                { lat: 25.3, lon: 51.2, zoom: 9 },
  "United Arab Emirates": { lat: 23.4, lon: 53.8, zoom: 7 },
  "Oman":                 { lat: 21.5, lon: 55.9, zoom: 6 },
};

// ── REGIONAL BUBBLE MAP ───────────────────────────────────────────────────────
async function renderHeatmap() {
  const params = buildParams();
  const data = await fetchJSON(`/api/map/bubbles?${params}`);
  const countries = data.countries || [];

  if (countries.length === 0) {
    document.getElementById("map-container").innerHTML =
      '<p style="padding:40px;text-align:center;color:#666">No data for current filters.</p>';
    return;
  }

  // Build traces...
  const byType = {};
  countries.forEach((c) => {
    const type = c.dominant_type || "Strategic developments";
    if (!byType[type]) byType[type] = [];
    byType[type].push(c);
  });

  const traces = EVENT_ORDER
    .filter((etype) => byType[etype])
    .map((etype) => {
      const items = byType[etype];
      return {
        type: "scattermapbox",
        name: etype,
        lat: items.map((c) => c.lat),
        lon: items.map((c) => c.lon),
        mode: "markers",
        marker: {
          size: items.map((c) => Math.max(8, Math.min(60, Math.sqrt(c.total_events) * 0.8))),
          color: EVENT_COLORS[etype] || "#888",
          opacity: 0.8,
          sizemode: "diameter",
        },
        text: items.map(
          (c) =>
            `<b>${c.country}</b><br>` +
            `─────────────────<br>` +
            `📍 Events: <b>${c.total_events.toLocaleString()}</b><br>` +
            `💔 Fatalities: <b>${c.total_fatalities.toLocaleString()}</b><br>` +
            `⚡ Dominant type: <b>${c.dominant_type}</b><br>` +
            `<i>Click to zoom into this country</i>`
        ),
        hoverinfo: "text",
        hoverlabel: {
          bgcolor: "white",
          bordercolor: EVENT_COLORS[etype] || "#888",
          font: { family: "Poppins, sans-serif", size: 12, color: "#1a1a1a" },
          align: "left",
        },
        customdata: items.map((c) => c.country),
      };
    });

  const periodLabel = state.showAll
    ? "Full Period (Jan 2024–Apr 2025)"
    : state.period === "day"
    ? `Day: ${state.weeks[state.weekIdx]}`
    : state.period === "week"
    ? `Week of ${state.weeks[state.weekIdx]}`
    : `Month: ${state.weeks[state.weekIdx]}`;

  const layout = {
    mapbox: { style: "carto-positron", center: { lat: 28, lon: 42 }, zoom: 3.8 },
    margin: { l: 0, r: 0, t: 40, b: 0 },
    height: 560,
    showlegend: true,
    legend: {
      title: { text: "<b>Dominant Event Type</b>", font: { size: 13, family: "Poppins" } },
      bgcolor: "rgba(255,255,255,0.95)",
      bordercolor: "#ddd",
      borderwidth: 1,
      x: 0, y: 1,
      font: { family: "Poppins, sans-serif", size: 12 },
      itemsizing: "constant",
    },
    annotations: [{
      x: 0.01, y: 0.01,
      xref: "paper", yref: "paper",
      text: "Bubble size = number of events · Click bubble to zoom into country",
      showarrow: false,
      font: { family: "Poppins", size: 11, color: "#666" },
      bgcolor: "rgba(255,255,255,0.85)",
      borderpad: 4,
    }],
    title: {
      text: `Middle East Conflict — ${periodLabel}`,
      x: 0.5,
      font: { size: 14, family: "Poppins" },
    },
  };

  // if (!mapInitialized) {
  //   Plotly.newPlot("map-container", traces, layout, { responsive: true });
  //   mapInitialized = true;
  //   document.getElementById("map-container").on("plotly_click", function (eventData) {
  //     if (eventData.points && eventData.points[0]) {
  //       const country = eventData.points[0].customdata;
  //       if (country) {
  //         state.drillCountry = country;
  //         state.mapMode = "detail";
  //         mapInitialized = false;
  //         document.getElementById("btn-heatmap").classList.remove("active");
  //         document.getElementById("btn-detail").classList.add("active");
  //         document.getElementById("btn-back").style.display = "inline-block";
  //         document.getElementById("country-drill").style.display = "inline-block";
  //         document.getElementById("country-drill").value = country;
  //         renderDetailMap();
  //       }
  //     }
  //   });
  // } else {
  //   Plotly.react("map-container", traces, layout);
  // }
  // KEY FIX: Always use newPlot when switching to heatmap mode
  if (currentMapMode !== "heatmap") {
    Plotly.newPlot("map-container", traces, layout, { responsive: true });
    currentMapMode = "heatmap";
    mapInitialized = true;
    
    // Re-attach click handler
    document.getElementById("map-container").on("plotly_click", function (eventData) {
        if (eventData.points && eventData.points[0]) {
            const country = eventData.points[0].customdata;
            if (country) {
                state.drillCountry = country;
                state.mapMode = "detail";
                document.getElementById("btn-heatmap").classList.remove("active");
                document.getElementById("btn-detail").classList.add("active");
                document.getElementById("btn-back").style.display = "inline-block";
                document.getElementById("country-drill").style.display = "inline-block";
                document.getElementById("country-drill").value = country;
                renderDetailMap();
            }
        }
    });
  } else {
      Plotly.react("map-container", traces, layout);
  }
}


// ── COUNTRY DETAIL MAP ────────────────────────────────────────────────────────
async function renderDetailMap() {
  const country = state.drillCountry;
  if (!country) {
    document.getElementById("map-container").innerHTML =
      '<p style="padding:40px;color:#666;text-align:center;font-size:14px">👆 Select a country from the dropdown above to zoom in.</p>';
    return;
  }

  const params = new URLSearchParams();
  params.set("country", country);
  if (state.eventTypes.length) params.set("event_types", state.eventTypes.join(","));
  if (state.dateFrom) params.set("date_from", state.dateFrom);
  if (state.dateTo)   params.set("date_to",   state.dateTo);
  if (!state.showAll && state.weeks.length) {
    params.set("period",       state.period);
    params.set("period_value", state.weeks[state.weekIdx]);
  }

  const data   = await fetchJSON(`/api/map/events?${params}`);
  const events = data.events || [];

  const byType = {};
  events.forEach((e) => {
    if (!byType[e.event_type]) byType[e.event_type] = [];
    byType[e.event_type].push(e);
  });

  const traces = EVENT_ORDER
    .filter((etype) => byType[etype])
    .map((etype) => {
      const evts = byType[etype];
      return {
        type: "scattermapbox",
        name: etype,
        lat:  evts.map((e) => e.latitude),
        lon:  evts.map((e) => e.longitude),
        mode: "markers",
        marker: {
          size:    evts.map((e) => Math.min(5 + (e.fatalities || 0) * 2, 30)),
          color:   EVENT_COLORS[etype] || "#888",
          opacity: 0.8,
        },
        text: evts.map(
          (e) =>
            `<b>${e.location}</b><br>` +
            `─────────────────<br>` +
            `📅 <b>Date:</b> ${e.date_str}<br>` +
            `⚡ <b>Type:</b> ${e.event_type}<br>` +
            `🔍 <b>Sub-type:</b> ${e.sub_event_type || "N/A"}<br>` +
            `💔 <b>Fatalities:</b> ${e.fatalities}<br>` +
            `👤 <b>Actor:</b> ${e.actor1 || "Unknown"}<br>` +
            `📍 <b>Region:</b> ${e.admin1 || "N/A"}`
        ),
        hoverinfo: "text",
        hoverlabel: {
          bgcolor:     "white",
          bordercolor: EVENT_COLORS[etype] || "#888",
          font: { family: "Poppins, sans-serif", size: 12, color: "#1a1a1a" },
          align: "left",
        },
      };
    });

  const c = COUNTRY_CENTERS[country] || { lat: 29, lon: 40, zoom: 5 };
  const periodLabel = state.showAll ? "Full Period" : state.weeks[state.weekIdx] || "";

  const layout = {
    mapbox: { style: "carto-positron", center: { lat: c.lat, lon: c.lon }, zoom: c.zoom },
    margin: { l: 0, r: 0, t: 40, b: 0 },
    height: 560,
    legend: {
      title: { text: "<b>Event Type</b>", font: { size: 13, family: "Poppins" } },
      bgcolor: "rgba(255,255,255,0.95)",
      bordercolor: "#ddd",
      borderwidth: 1,
      x: 0, y: 1,
      font: { family: "Poppins, sans-serif", size: 12 },
      itemsizing: "constant",
      itemwidth: 40,
    },
    annotations: [{
      x: 0.01, y: 0.01,
      xref: "paper", yref: "paper",
      text: "● small = 0 fatalities  ⬤ large = many fatalities",
      showarrow: false,
      font: { family: "Poppins", size: 11, color: "#666" },
      bgcolor: "rgba(255,255,255,0.8)",
      borderpad: 4,
    }],
    title: {
      text: `${country} — ${periodLabel}`,
      x: 0.5,
      font: { size: 13, family: "Poppins" },
    },
  };

  // if (!mapInitialized) {
  //   Plotly.newPlot("map-container", traces, layout, { responsive: true });
  //   mapInitialized = true;
  // } else {
  //   Plotly.react("map-container", traces, layout);
  // }
  Plotly.newPlot("map-container", traces, layout, { responsive: true });
  currentMapMode = "detail";
  mapInitialized = true;
}