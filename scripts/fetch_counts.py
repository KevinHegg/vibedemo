#!/usr/bin/env python3

"""Generate data.json for the LOC Chronicling America demo."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://www.loc.gov/collections/chronicling-america/"
TERM = "influenza"
YEAR_RANGE = range(1910, 1926)
MAP_YEAR = 1918
REQUESTS_PER_MINUTE = 18
REQUEST_DELAY_SECONDS = 60 / REQUESTS_PER_MINUTE
MAX_RETRIES = 5
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data.json"
USER_AGENT = "Mozilla/5.0 (compatible; vibedemo-fetcher/1.0; +https://github.com/KevinHegg/vibedemo)"

# The prompt asked for front_pages_only and location_state. The current
# collection API count endpoint appears to ignore those direct parameters, so
# the script records the requested parameters for provenance and uses the
# supported location facet filter for state counts.
REQUESTED_QUERY_PARAMS = {
    "q": TERM,
    "dates": "YYYY/YYYY",
    "front_pages_only": "true",
    "location_state": "<state name>",
    "at": "pagination",
    "fo": "json",
    "c": "1",
}

STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def throttle(last_request_at: float | None) -> float:
    if last_request_at is not None:
        elapsed = time.time() - last_request_at
        remaining = REQUEST_DELAY_SECONDS - elapsed
        if remaining > 0:
            time.sleep(remaining)
    return time.time()


def request_json(params: dict[str, str], *, last_request_at: float | None) -> tuple[dict, float]:
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    request_at = throttle(last_request_at)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request) as response:
                payload = json.load(response)
                return payload, request_at
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == MAX_RETRIES - 1:
                raise

            retry_after = exc.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else REQUEST_DELAY_SECONDS * (attempt + 2)
            time.sleep(sleep_for)
            request_at = time.time()
        except urllib.error.URLError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(REQUEST_DELAY_SECONDS * (attempt + 2))
            request_at = time.time()

    raise RuntimeError(f"Unable to fetch {url}")


def extract_count(payload: dict) -> int:
    pagination = payload.get("pagination", {})
    if "of" in pagination:
        return int(pagination["of"])
    if "total" in pagination:
        return int(pagination["total"])
    raise KeyError("pagination.of and pagination.total were both missing")


def count_for_year(year: int, *, last_request_at: float | None) -> tuple[int, float]:
    params = {
        "fo": "json",
        "c": "1",
        "at": "pagination",
        "q": TERM,
        "dates": f"{year}/{year}",
        "front_pages_only": "true",
    }
    payload, request_at = request_json(params, last_request_at=last_request_at)
    return extract_count(payload), request_at


def count_for_state(year: int, abbreviation: str, state_name: str, *, last_request_at: float | None) -> tuple[int, float]:
    params = {
        "fo": "json",
        "c": "1",
        "at": "pagination",
        "q": TERM,
        "dates": f"{year}/{year}",
        "front_pages_only": "true",
        "location_state": state_name.lower(),
        # Facet filtering is the piece that currently affects counts.
        "fa": f"location:{state_name.lower()}",
    }
    payload, request_at = request_json(params, last_request_at=last_request_at)
    return extract_count(payload), request_at


def build_data() -> dict:
    last_request_at = None
    national = []

    for year in YEAR_RANGE:
        count, last_request_at = count_for_year(year, last_request_at=last_request_at)
        national.append({"year": year, "count": count})
        print(f"National {year}: {count}", file=sys.stderr)

    by_state = {}
    for abbreviation, state_name in STATE_NAMES.items():
        count, last_request_at = count_for_state(
            MAP_YEAR,
            abbreviation,
            state_name,
            last_request_at=last_request_at,
        )
        by_state[abbreviation] = count
        print(f"{MAP_YEAR} {abbreviation} ({state_name}): {count}", file=sys.stderr)

    return {
        "term": TERM,
        "year_range": [YEAR_RANGE.start, YEAR_RANGE.stop - 1],
        "map_year": MAP_YEAR,
        "query_params": {
            "requested": REQUESTED_QUERY_PARAMS,
            "effective": {
                "national": {
                    "fo": "json",
                    "c": "1",
                    "at": "pagination",
                    "q": TERM,
                    "dates": "YYYY/YYYY",
                    "front_pages_only": "true",
                },
                "by_state": {
                    "fo": "json",
                    "c": "1",
                    "at": "pagination",
                    "q": TERM,
                    "dates": f"{MAP_YEAR}/{MAP_YEAR}",
                    "front_pages_only": "true",
                    "location_state": "<state name>",
                    "fa": "location:<state name>",
                },
            },
            "notes": [
                "Counts come from pagination.of on the loc.gov collection endpoint.",
                "The collection endpoint currently appears to ignore front_pages_only and direct location_state parameters for count changes.",
                "State snapshot counts therefore rely on the supported fa=location:<state name> facet filter while preserving the requested parameters in metadata.",
            ],
        },
        "national": national,
        "by_state": by_state,
    }


def main() -> int:
    data = build_data()
    OUTPUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
