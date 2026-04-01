#!/usr/bin/env python3
"""Fetch public Densho oral history transcript sources and metadata."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://ddr.densho.org"
API_HEADERS = {
    "User-Agent": "vibedemo-oralhistorynlp/1.0 (+https://github.com/KevinHegg/vibedemo)",
    "Accept": "application/json",
}


def fetch_bytes(url: str, retries: int = 3, pause: float = 0.25) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers=API_HEADERS)
            with urlopen(request, timeout=60) as response:
                payload = response.read()
            time.sleep(pause)
            return payload
        except (HTTPError, URLError) as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(pause * (attempt + 2))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_bytes(url).decode("utf-8", "replace"))


def fetch_paginated(url: str, limit: int = 100) -> Iterable[dict]:
    offset = 0
    while True:
        sep = "&" if "?" in url else "?"
        page_url = f"{url}{sep}{urlencode({'limit': limit, 'offset': offset})}"
        page = fetch_json(page_url)
        for obj in page.get("objects", []):
            yield obj
        next_offset = page.get("next_offset")
        if next_offset is None:
            return
        offset = next_offset


def absolute_media_url(interview_id: str, file_obj: dict) -> str:
    links = file_obj.get("links", {})
    if links.get("img", "").startswith("https://"):
        return links["img"]
    collection_id = "-".join(interview_id.split("-")[:3])
    filename = file_obj.get("download_large") or file_obj["id"]
    return f"{BASE_URL}/media/{collection_id}/{filename}"


def transcript_files(interview_id: str, files_url: str) -> List[dict]:
    results: List[dict] = []
    for file_obj in fetch_paginated(files_url, limit=100):
        haystack = " ".join(
            [
                file_obj.get("id", ""),
                file_obj.get("title", ""),
                file_obj.get("download_large", ""),
            ]
        ).lower()
        if "transcript" not in haystack:
            continue
        media_url = absolute_media_url(interview_id, file_obj)
        results.append(
            {
                "file_id": file_obj.get("id"),
                "title": file_obj.get("title", ""),
                "media_url": media_url,
                "html_url": file_obj.get("links", {}).get("html", ""),
                "json_url": file_obj.get("links", {}).get("json", ""),
            }
        )
    return results


def choose_topics(entity: dict) -> List[str]:
    topics = []
    for topic in entity.get("topics", []) or []:
        label = topic.get("term") or topic.get("title") or topic.get("name")
        if label:
            topics.append(label)
    return topics


def choose_generation(entity: dict) -> str:
    fields = [
        entity.get("title", ""),
        entity.get("description", ""),
        " ".join(choose_topics(entity)),
    ]
    joined = " ".join(fields).lower()
    for generation in ["issei", "nisei", "sansei", "yonsei", "kibei", "nissei"]:
        if generation in joined:
            return generation.capitalize()
    return ""


def narrator_name(entity: dict) -> str:
    for creator in entity.get("creators", []) or []:
        if creator.get("role") == "narrator":
            return creator.get("namepart", "")
    title = entity.get("title", "")
    if title.endswith(" Interview"):
        return title[: -len(" Interview")]
    return title


def write_raw_file(raw_dir: Path, interview_id: str, transcript: dict) -> Path:
    suffix = Path(transcript["media_url"]).suffix or ".bin"
    target_dir = raw_dir / interview_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{transcript['file_id']}{suffix}"
    if not target_path.exists():
        target_path.write_bytes(fetch_bytes(transcript["media_url"], pause=0.15))
    return target_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-interviews", type=int, default=15)
    parser.add_argument("--output-dir", default="data/oralhistorynlp")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    interviews: Dict[str, dict] = {}
    narrators_url = f"{BASE_URL}/api/0.2/narrator/"

    for narrator in fetch_paginated(narrators_url, limit=100):
        interviews_url = narrator.get("links", {}).get("interviews")
        if not interviews_url:
            continue
        interviews_page = fetch_json(interviews_url)
        for interview_stub in interviews_page.get("objects", []):
            interview_id = interview_stub.get("id")
            if not interview_id or interview_id in interviews:
                continue
            entity_url = interview_stub.get("links", {}).get("json")
            if not entity_url:
                continue
            entity = fetch_json(entity_url)
            transcript_list = transcript_files(
                interview_id,
                entity.get("links", {}).get("children-files", ""),
            )
            if not transcript_list:
                continue
            raw_files = []
            for transcript in transcript_list:
                raw_path = write_raw_file(raw_dir, interview_id, transcript)
                transcript["local_path"] = str(raw_path)
                raw_files.append(str(raw_path))
            interviews[interview_id] = {
                "interview_id": interview_id,
                "title": entity.get("title", ""),
                "interviewee": narrator_name(entity),
                "interview_url": entity.get("links", {}).get("html", ""),
                "json_url": entity_url,
                "collection_id": entity.get("collection_id", ""),
                "creation": entity.get("creation", ""),
                "location": entity.get("location", ""),
                "description": entity.get("description", ""),
                "generation": choose_generation(entity),
                "topics": choose_topics(entity),
                "creators": entity.get("creators", []),
                "transcripts": transcript_list,
                "raw_files": raw_files,
            }
            print(f"Collected {len(interviews):>3} {interview_id} {entity.get('title', '')}", flush=True)
            if len(interviews) >= args.max_interviews:
                break
        if len(interviews) >= args.max_interviews:
            break

    if len(interviews) < 75:
        raise SystemExit(
            f"Only collected {len(interviews)} transcript-bearing interviews; below the minimum threshold of 75."
        )

    interviews_path = output_dir / "interviews_raw.json"
    interviews_path.write_text(
        json.dumps(
            {
                "source": "Densho Digital Repository public narrator and entity API",
                "sample_size": len(interviews),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "interviews": list(interviews.values()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest_path = output_dir / "sources_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "interview_id",
                "interviewee",
                "title",
                "creation",
                "location",
                "generation",
                "interview_url",
                "json_url",
                "transcript_title",
                "transcript_media_url",
            ],
        )
        writer.writeheader()
        for interview in interviews.values():
            for transcript in interview["transcripts"]:
                writer.writerow(
                    {
                        "interview_id": interview["interview_id"],
                        "interviewee": interview["interviewee"],
                        "title": interview["title"],
                        "creation": interview["creation"],
                        "location": interview["location"],
                        "generation": interview["generation"],
                        "interview_url": interview["interview_url"],
                        "json_url": interview["json_url"],
                        "transcript_title": transcript["title"],
                        "transcript_media_url": transcript["media_url"],
                    }
                )

    print(f"Wrote {interviews_path}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
