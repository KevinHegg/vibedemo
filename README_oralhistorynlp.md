# Oral History NLP Demo

This demo is a static, reproducible classroom page inspired by the claim that NLP over Densho oral history transcripts can surface patterns in location, topics, and sentiment.

## Data source

- Public Densho Digital Repository narrator and entity API endpoints.
- Public transcript files linked from those interview records.
- The source manifest lives at `data/oralhistorynlp/sources_manifest.csv`.

## Sample size

- The checked-in build analyzes **339 usable public transcript segments drawn from 15 Densho oral history interviews**.
- The exact sample size is also written into `data/oralhistorynlp/dashboard-data.json` and displayed on `oralhistorynlp.html`.
- Because Densho often exposes public transcripts as segmented transcript files, this demo reports both the number of usable transcript segments and the number of interviews they came from.

## Methods

- `scripts/fetch_densho_transcripts.py` discovers narrator records, follows interview links, finds public transcript files, downloads raw transcript files outside git, and writes metadata plus a source manifest.
- `scripts/analyze_oral_histories.py` extracts transcript text, normalizes basic metadata, computes transcript-segment lengths, runs VADER sentiment, and fits an NMF topic model over TF-IDF text features.
- The static page reads precomputed data from `data/oralhistorynlp/dashboard-data.js`.

## Limitations

- This is not claimed as an exact replication of Chen et al. unless the corpus size and methods happen to match exactly.
- The demo prefers publicly accessible transcripts only, so the final corpus may be smaller than 904 and may be represented as transcript segments rather than one bundled file per interview.
- Metadata normalization is intentionally conservative.
- Sentiment scores are rough transcript-level signals, not judgments about lived experience.

## How to rebuild

1. Install dependencies:
   `python3 -m pip install -r requirements-oralhistorynlp.txt`
2. Fetch transcript sources:
   `python3 scripts/fetch_densho_transcripts.py --max-interviews 15`
3. Analyze and write static data:
   `python3 scripts/analyze_oral_histories.py`
4. Serve locally:
   `python3 -m http.server 8000`
