# Live Demo Prompt

Use this file as the source prompt for the live Codex demo in this repo.

## Demo reminders

- Keep the existing fallback test implementation in place unless explicitly asked to remove it.
- Treat this as the live run, not the fallback run.
- Use fresh filenames for the live output instead of overwriting `index-test.html`, `data.json`, or `map.js` from the fallback implementation.
- After creating the live output, update the root `index.html` landing page so it links to the new live files.
- Make the generated page work well on both desktop and mobile.
- Stay transparent if the `loc.gov` collection endpoint does not honor a requested parameter exactly as written.

## Prompt

You are Codex in a repo. Build a static web demo using the Library of Congress loc.gov API (Chronicling America).
Goal: create a JS visualization that shows:
(1) a NATIONAL time series of yearly hit counts for a search term, and
(2) a US state choropleth for a single selected year (snapshot), based on the same term.
Use ONLY public data (no keys). Be careful with rate limits: keep requests < 20/min and use at=pagination to read total counts.

TERM = "influenza"
YEAR_RANGE = 1910..1925
MAP_YEAR = 1918
FILTER = front_pages_only=true
ENDPOINT = https://www.loc.gov/collections/chronicling-america/

Tasks:
1. Create data.json with:
   - term, year_range, map_year, query_params used
   - national: [{year, count}...]
   - by_state: { "AL": count, ... } for MAP_YEAR only
2. Create index.html that loads D3 (CDN) + TopoJSON (CDN), loads data.json, and renders:
   - line chart (national counts over time)
   - choropleth map of states for MAP_YEAR with tooltip (state + count)
3. Create map.js (loaded by index.html) containing ALL visualization logic (chart + map).
   Keep it readable; add comments.
4. Add a tiny local-run instruction in index.html (comment): python -m http.server 8000
5. Add a scripts/fetch_counts.js (or .py) that generates data.json by calling the loc.gov API.
   - For national counts, one request per year using at=pagination.
   - For map counts, one request per state for MAP_YEAR using location_state=<state name> and at=pagination.
   - Parse pagination.of (or pagination.total if needed).
   - Throttle requests (sleep) and retry on HTTP 429/5xx.
6. Provide a short README section at bottom of README.md describing what you created and how to run it.

Expected repo outputs (must exist): index.html, data.json, map.js
Now implement.
