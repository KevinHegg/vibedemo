(function () {
  const data = window.ORAL_HISTORY_NLP_DATA;
  if (!data) {
    document.getElementById("app").innerHTML =
      "<p>The precomputed dataset did not load. Serve the repo with <code>python -m http.server</code> if your browser blocks local script loading.</p>";
    return;
  }

  const statGrid = document.getElementById("stat-grid");
  const topicList = document.getElementById("topic-list");
  const topicDetail = document.getElementById("topic-detail");
  const corpusNote = document.getElementById("corpus-note");

  const summary = data.summary;
  const stats = [
    ["Transcript segments analyzed", summary.sample_size.toLocaleString()],
    ["Unique interviews represented", summary.unique_interviews.toLocaleString()],
    ["Total words", summary.total_words.toLocaleString()],
    ["Year range", `${summary.year_range[0]} to ${summary.year_range[1]}`],
    ["Unique locations", summary.unique_locations.toLocaleString()],
  ];

  stats.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "stat-pill";
    item.textContent = `${label}: ${value}`;
    statGrid.appendChild(item);
  });

  if (corpusNote) {
    corpusNote.innerHTML =
      `<strong>This checked-in build uses ${summary.sample_size.toLocaleString()} usable public transcript segments drawn from ${summary.unique_interviews.toLocaleString()} Densho interviews.</strong>`;
  }

  Plotly.newPlot(
    "location-chart",
    [
      {
        type: "bar",
        orientation: "h",
        y: data.location_patterns.map((row) => row.location).reverse(),
        x: data.location_patterns.map((row) => row.count).reverse(),
        marker: {
          color: data.location_patterns.map((row) => row.avg_sentiment).reverse(),
          colorscale: [
            [0, "#5e7f89"],
            [0.5, "#d7d9dc"],
            [1, "#a3472f"],
          ],
          colorbar: { title: "Avg sentiment" },
        },
        hovertemplate:
          "<b>%{y}</b><br>Transcript segments: %{x}<br>Avg sentiment: %{marker.color:.2f}<extra></extra>",
      },
    ],
    baseLayout("Location Patterns", { l: 170, r: 30, t: 48, b: 40 })
  );

  Plotly.newPlot(
    "sentiment-chart",
    [
      {
        type: "histogram",
        x: data.sentiment_rows.map((row) => row.sentiment),
        marker: { color: "#8b3f2e" },
        nbinsx: 18,
        hovertemplate: "Sentiment bin: %{x}<br>Transcript segments: %{y}<extra></extra>",
      },
    ],
    baseLayout("Sentiment Distribution", { l: 50, r: 20, t: 48, b: 48 }, {
      xaxis: { title: "VADER compound score" },
      yaxis: { title: "Transcript count" },
    })
  );

  Plotly.newPlot(
    "timeline-chart",
    [
      {
        type: "scatter",
        mode: "lines+markers",
        x: data.year_counts.map((row) => row.year),
        y: data.year_counts.map((row) => row.count),
        line: { color: "#8b3f2e", width: 3 },
        marker: { color: "#203038", size: 8 },
        hovertemplate: "Interview year: %{x}<br>Transcript segments: %{y}<extra></extra>",
      },
    ],
    baseLayout("Interview Dates Over Time", { l: 50, r: 20, t: 48, b: 48 }, {
      xaxis: { title: "Interview year" },
      yaxis: { title: "Transcript count" },
    })
  );

  Plotly.newPlot(
    "scatter-chart",
    [
      {
        type: "scatter",
        mode: "markers",
        x: data.sentiment_rows.map((row) => row.word_count),
        y: data.sentiment_rows.map((row) => row.sentiment),
        text: data.sentiment_rows.map(
          (row) => `${row.interviewee}<br>${row.location}<br>Topic ${row.topic_id + 1}`
        ),
        marker: {
          size: 10,
          color: data.sentiment_rows.map((row) => row.topic_id),
          colorscale: "Earth",
          opacity: 0.82,
        },
        hovertemplate: "%{text}<br>Words: %{x}<br>Sentiment: %{y:.2f}<extra></extra>",
      },
    ],
    baseLayout("Transcript Length vs Sentiment", { l: 58, r: 20, t: 48, b: 52 }, {
      xaxis: { title: "Transcript word count" },
      yaxis: { title: "Sentiment score" },
    })
  );

  data.topics.forEach((topic, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `topic-button${index === 0 ? " is-active" : ""}`;
    button.innerHTML = `
      <strong>Topic ${index + 1}</strong>
      <div class="topic-keywords">${topic.keywords.slice(0, 6).join(", ")}</div>
    `;
    button.addEventListener("click", () => {
      document
        .querySelectorAll(".topic-button")
        .forEach((node) => node.classList.remove("is-active"));
      button.classList.add("is-active");
      renderTopic(topic, index);
    });
    topicList.appendChild(button);
  });

  renderTopic(data.topics[0], 0);

  function renderTopic(topic, index) {
    const reps = topic.representatives
      .map(
        (rep) => `
          <article class="rep-card">
            <strong>${rep.interviewee}</strong>
            <div class="topic-keywords">${rep.location}${rep.year ? ` • ${rep.year}` : ""} • ${rep.word_count.toLocaleString()} words • sentiment ${rep.sentiment}</div>
            <p>${escapeHtml(rep.excerpt)}</p>
          </article>
        `
      )
      .join("");
    topicDetail.innerHTML = `
      <h3>Topic ${index + 1}: ${escapeHtml(topic.label)}</h3>
      <p class="subtle">This topic comes from an NMF model over transcript text. The labels are generated from the highest-weighted terms, so they are summaries rather than human-authored archival categories.</p>
      <div class="topic-summary">
        <span class="mini-pill">Prevalence: ${topic.prevalence} transcript segments</span>
        <span class="mini-pill">Share of corpus: ${(topic.share * 100).toFixed(1)}%</span>
        <span class="mini-pill">Average sentiment: ${topic.avg_sentiment}</span>
      </div>
      <p class="topic-keywords"><strong>Top keywords:</strong> ${topic.keywords.join(", ")}</p>
      <div class="rep-list">${reps}</div>
    `;
  }

  document.getElementById("method-notes").innerHTML = data.method_notes
    .map((note) => `<li>${escapeHtml(note)}</li>`)
    .join("");

  function baseLayout(title, margin, extra) {
    return Object.assign(
      {
        title: { text: title, x: 0, font: { family: "Georgia, serif", size: 20, color: "#1d2b2f" } },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "Arial, sans-serif", color: "#59686d" },
        margin,
      },
      extra || {}
    );
  }

  function escapeHtml(text) {
    return String(text || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }
})();
