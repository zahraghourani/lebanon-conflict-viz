let mapInitialized = false;
const EVENT_COLORS = {
  "Explosions/Remote violence": "#d62728",
  Battles: "#ff7f0e",
  "Violence against civilians": "#9467bd",
  Protests: "#2ca02c",
  Riots: "#8c564b",
  "Strategic developments": "#888888",
};

async function renderHeatmap() {
  const params = buildParams();
  const data = await fetchJSON(`/api/map/heatmap?${params}`);
  const points = data.points || [];

  const trace = {
    type: "densitymapbox",
    lat: points.map((p) => p.lat),
    lon: points.map((p) => p.lon),
    z: points.map((p) => p.weight),
    radius: 25,
    colorscale: [
      [0, "#ffffcc"],
      [0.2, "#fed976"],
      [0.4, "#feb24c"],
      [0.6, "#fd8d3c"],
      [0.8, "#e31a1c"],
      [1, "#800026"],
    ],
    showscale: false,
    opacity: 0.8,
    hovertemplate:
      "<b>Hotspot intensity</b><br>" +
      "📍 Latitude: %{lat:.3f}<br>" +
      "📍 Longitude: %{lon:.3f}<br>" +
      "⚖️ Weight: %{z:.0f}<extra></extra>",
    hoverlabel: {
      bgcolor: "white",
      bordercolor: "#888",
      font: { family: "Poppins, sans-serif", size: 12, color: "#1a1a1a" },
      align: "left",
    },
  };

  const layout = {
    mapbox: {
      style: "carto-positron",
      center: { lat: 29, lon: 40 },
      zoom: 4,
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    height: 560,
    legend: {
      title: { text: "<b>Dominant Event Type</b>", font: { size: 13, family: "Poppins" } },
      bgcolor: "rgba(255,255,255,0.95)",
      bordercolor: "#ddd",
      borderwidth: 1,
      x: 0,
      y: 1,
      font: { family: "Poppins, sans-serif", size: 12 },
      itemsizing: "constant",
    },
    annotations: [
      {
        x: 0.01,
        y: 0.01,
        xref: "paper",
        yref: "paper",
        text: "Bubble size = number of events · Click bubble to zoom into country",
        showarrow: false,
        font: { family: "Poppins", size: 11, color: "#666" },
        bgcolor: "rgba(255,255,255,0.85)",
        borderpad: 4,
      },
    ],
    title: {
      text: state.showAll
        ? "Conflict Hotspots — Full Period (Jan 2024–Apr 2025)"
        : `Conflict Hotspots — Week of ${state.weeks[state.weekIdx] || ""}`,
      x: 0.5,
      font: { size: 13 },
    },
  };

  if (!mapInitialized) {
    Plotly.newPlot('map-container', traces, layout, {responsive: true});
    mapInitialized = true;
  } else {
      Plotly.react('map-container', traces, layout);
  }
}

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
  if (state.dateTo) params.set("date_to", state.dateTo);
  if (!state.showAll && state.weeks.length) params.set("week", state.weeks[state.weekIdx]);

  const data = await fetchJSON(`/api/map/events?${params}`);
  const events = data.events || [];

  const byType = {};
  events.forEach((e) => {
    if (!byType[e.event_type]) byType[e.event_type] = [];
    byType[e.event_type].push(e);
  });

  const traces = Object.entries(byType).map(([etype, evts]) => ({
    type: "scattermapbox",
    name: etype,
    lat: evts.map((e) => e.latitude),
    lon: evts.map((e) => e.longitude),
    mode: "markers",
    marker: {
      size: evts.map((e) => Math.min(5 + (e.fatalities || 0) * 2, 30)),
      color: EVENT_COLORS[etype] || "#888",
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
      bgcolor: "white",
      bordercolor: EVENT_COLORS[etype] || "#888",
      font: { family: "Poppins, sans-serif", size: 12, color: "#1a1a1a" },
      align: "left",
    },
  }));

  const CENTERS = {
    "Occupied Palestine": { lat: 31.9, lon: 35.2, zoom: 8 },
    Lebanon: { lat: 33.9, lon: 35.5, zoom: 8 },
    Syria: { lat: 34.8, lon: 38.9, zoom: 6 },
    Yemen: { lat: 15.6, lon: 48.5, zoom: 6 },
    Iraq: { lat: 33.2, lon: 43.7, zoom: 6 },
    Iran: { lat: 32.4, lon: 53.7, zoom: 5 },
    Turkey: { lat: 38.9, lon: 35.2, zoom: 5 },
    Jordan: { lat: 30.6, lon: 36.5, zoom: 7 },
    Egypt: { lat: 26.8, lon: 30.8, zoom: 5 },
    Libya: { lat: 26.3, lon: 17.2, zoom: 5 },
    "Saudi Arabia": { lat: 23.9, lon: 45.1, zoom: 5 },
  };
  const c = CENTERS[country] || { lat: 29, lon: 40, zoom: 5 };

  const layout = {
    mapbox: { style: "carto-positron", center: { lat: c.lat, lon: c.lon }, zoom: c.zoom },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    height: 560,
    legend: {
      title: { text: "<b>Event Type</b>", font: { size: 13, family: "Poppins" } },
      bgcolor: "rgba(255,255,255,0.95)",
      bordercolor: "#ddd",
      borderwidth: 1,
      x: 0,
      y: 1,
      font: { family: "Poppins, sans-serif", size: 12 },
      itemsizing: "constant",
      itemwidth: 40,
    },
    annotations: [
      {
        x: 0.01,
        y: 0.01,
        xref: "paper",
        yref: "paper",
        text: "● small = 0 fatalities  ⬤ large = many fatalities",
        showarrow: false,
        font: { family: "Poppins", size: 11, color: "#666" },
        bgcolor: "rgba(255,255,255,0.8)",
        borderpad: 4,
      },
    ],
    title: {
      text: `${country} — ${state.showAll ? "Full Period" : state.weeks[state.weekIdx] || ""}`,
      x: 0.5,
      font: { size: 13 },
    },
  };

  Plotly.react("map-container", traces, layout, { responsive: true });
}
