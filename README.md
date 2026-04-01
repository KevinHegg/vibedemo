# vibedemo

## LOC Chronicling America prompt test

This repo now includes a standalone test page for a live demo prompt that turns
Library of Congress Chronicling America counts into two linked views:

- `index-test.html` renders a national yearly line chart plus a state choropleth.
- `map.js` contains the D3 + TopoJSON visualization logic.
- `data.json` stores the generated counts for the `influenza` query.
- `scripts/fetch_counts.py` regenerates `data.json` from the public `loc.gov` API.
- `prompt.md` stores the classroom-ready live prompt with reminders for the real run.

Run it locally with `python3 -m http.server 8000` from the repo root, then open
`http://localhost:8000/index-test.html`.

Refresh the dataset with `python3 scripts/fetch_counts.py`. The script throttles
requests to stay below 20 per minute and reads totals from `pagination.of`.
