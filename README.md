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

## LOC Chronicling America live build

The real live-run output now lives in fresh files instead of overwriting the fallback artifacts:

- `influenza.html` is the live static page for the classroom demo.
- `influenza-map.js` contains the D3 + TopoJSON logic for the live page.
- `influenza-data.json` stores the generated counts for the live `influenza` query.
- `scripts/fetch_influenza_counts.py` regenerates `influenza-data.json` from the public `loc.gov` API.

Run it locally with `python3 -m http.server 8000`, then open
`http://localhost:8000/influenza.html`.

Refresh the live dataset with `python3 scripts/fetch_influenza_counts.py`. The script
throttles requests to stay below 20 per minute, reads totals from `pagination.of`, and
documents the verified live behavior that `front_pages_only=true` and direct
`location_state=<state name>` did not change the tested counts while
`fa=location:<state name>` did.
