(async function main() {
  const data = await d3.json("data.json");
  const usAtlas = await d3.json("https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json");

  renderLineChart(data.national, data.term);
  renderChoropleth(usAtlas, data.by_state, data.map_year, data.term);
})().catch((error) => {
  console.error("Failed to render demo", error);

  const message = document.createElement("p");
  message.textContent = "Unable to load demo data right now.";
  message.style.color = "#9f3d2e";
  message.style.fontFamily = "Arial, sans-serif";

  document.querySelectorAll(".viz").forEach((node) => {
    node.innerHTML = "";
    node.appendChild(message.cloneNode(true));
  });
});

const STATE_ABBREVIATIONS_BY_FIPS = {
  1: "AL",
  2: "AK",
  4: "AZ",
  5: "AR",
  6: "CA",
  8: "CO",
  9: "CT",
  10: "DE",
  12: "FL",
  13: "GA",
  15: "HI",
  16: "ID",
  17: "IL",
  18: "IN",
  19: "IA",
  20: "KS",
  21: "KY",
  22: "LA",
  23: "ME",
  24: "MD",
  25: "MA",
  26: "MI",
  27: "MN",
  28: "MS",
  29: "MO",
  30: "MT",
  31: "NE",
  32: "NV",
  33: "NH",
  34: "NJ",
  35: "NM",
  36: "NY",
  37: "NC",
  38: "ND",
  39: "OH",
  40: "OK",
  41: "OR",
  42: "PA",
  44: "RI",
  45: "SC",
  46: "SD",
  47: "TN",
  48: "TX",
  49: "UT",
  50: "VT",
  51: "VA",
  53: "WA",
  54: "WV",
  55: "WI",
  56: "WY",
};

const STATE_NAMES_BY_ABBREVIATION = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
};

function renderLineChart(series, term) {
  const container = d3.select("#line-chart");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || 520;
  const height = 420;
  const margin = { top: 24, right: 18, bottom: 44, left: 62 };

  const x = d3
    .scaleLinear()
    .domain(d3.extent(series, (d) => d.year))
    .range([margin.left, width - margin.right]);

  const y = d3
    .scaleLinear()
    .domain([0, d3.max(series, (d) => d.count)])
    .nice()
    .range([height - margin.bottom, margin.top]);

  const line = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count));

  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img")
    .attr("aria-label", `Line chart of yearly ${term} results`);

  svg
    .append("g")
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .attr("class", "axis")
    .call(
      d3
        .axisBottom(x)
        .tickFormat(d3.format("d"))
        .tickValues(series.map((d) => d.year))
    )
    .call((g) => g.select(".domain").attr("stroke-opacity", 0.35));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left},0)`)
    .attr("class", "axis")
    .call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(",")))
    .call((g) => g.select(".domain").attr("stroke-opacity", 0.35));

  // A soft backdrop helps the line stand out without overloading the page.
  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", width - margin.left - margin.right)
    .attr("height", height - margin.top - margin.bottom)
    .attr("fill", "rgba(159, 61, 46, 0.05)")
    .attr("rx", 18);

  svg
    .append("path")
    .datum(series)
    .attr("class", "series-line")
    .attr("d", line);

  svg
    .append("g")
    .selectAll("circle")
    .data(series)
    .join("circle")
    .attr("class", "series-dot")
    .attr("cx", (d) => x(d.year))
    .attr("cy", (d) => y(d.count))
    .attr("r", 4.6)
    .append("title")
    .text((d) => `${d.year}: ${d3.format(",")(d.count)} hits`);
}

function renderChoropleth(usAtlas, byState, year, term) {
  const container = d3.select("#choropleth-map");
  container.selectAll("*").remove();

  const width = container.node().clientWidth || 520;
  const height = 420;
  const svg = container
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img")
    .attr("aria-label", `Choropleth map of ${term} results by state in ${year}`);

  const tooltip = container.append("div").attr("class", "tooltip");
  const states = topojson.feature(usAtlas, usAtlas.objects.states);
  const mesh = topojson.mesh(usAtlas, usAtlas.objects.states, (a, b) => a !== b);

  const projection = d3.geoAlbersUsa().fitSize([width, height - 38], states);
  const path = d3.geoPath(projection);
  const counts = Object.values(byState);
  const color = d3
    .scaleSequential()
    .domain([0, d3.max(counts)])
    .interpolator(d3.interpolateRgbBasis(["#f7ecd9", "#d49b6a", "#9f3d2e"]));

  svg
    .append("g")
    .selectAll("path")
    .data(states.features)
    .join("path")
    .attr("class", "state")
    .attr("fill", (feature) => {
      const abbreviation = STATE_ABBREVIATIONS_BY_FIPS[Number(feature.id)];
      const count = byState[abbreviation] ?? 0;
      return color(count);
    })
    .attr("d", path)
    .on("mousemove", function onMove(event, feature) {
      const abbreviation = STATE_ABBREVIATIONS_BY_FIPS[Number(feature.id)];
      const count = byState[abbreviation] ?? 0;
      const label = STATE_NAMES_BY_ABBREVIATION[abbreviation] || abbreviation;
      const [pointerX, pointerY] = d3.pointer(event, container.node());

      tooltip
        .classed("is-visible", true)
        .style("left", `${pointerX + 14}px`)
        .style("top", `${pointerY + 14}px`)
        .html(`<strong>${label}</strong><br>${d3.format(",")(count)} hits`);
    })
    .on("mouseleave", () => {
      tooltip.classed("is-visible", false);
    });

  svg
    .append("path")
    .datum(mesh)
    .attr("class", "state-borders")
    .attr("d", path);

  renderLegend(svg, color, width, height);
}

function renderLegend(svg, color, width, height) {
  const legendWidth = Math.min(240, width - 44);
  const legendHeight = 12;
  const legendX = 22;
  const legendY = height - 28;
  const steps = 120;
  const domain = color.domain();
  const legendScale = d3.scaleLinear().domain(domain).range([legendX, legendX + legendWidth]);

  const gradient = svg
    .append("defs")
    .append("linearGradient")
    .attr("id", "choropleth-gradient");

  d3.range(steps + 1).forEach((step) => {
    const t = step / steps;
    gradient
      .append("stop")
      .attr("offset", `${t * 100}%`)
      .attr("stop-color", color(domain[0] + t * (domain[1] - domain[0])));
  });

  svg
    .append("rect")
    .attr("x", legendX)
    .attr("y", legendY)
    .attr("width", legendWidth)
    .attr("height", legendHeight)
    .attr("rx", 999)
    .attr("fill", "url(#choropleth-gradient)");

  svg
    .append("g")
    .attr("class", "legend-axis")
    .attr("transform", `translate(0,${legendY + legendHeight})`)
    .call(d3.axisBottom(legendScale).ticks(4).tickFormat(d3.format(",")))
    .call((g) => g.select(".domain").remove());
}
