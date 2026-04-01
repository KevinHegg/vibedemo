#!/usr/bin/env python3
"""Analyze pre-fetched Densho oral history transcripts for a static demo."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from statistics import mean, median
from typing import Iterable, List

DEPS_PATH = os.environ.get("ORALHISTORYNLP_PY_DEPS", "/tmp/vibedemo_deps")
if DEPS_PATH and os.path.isdir(DEPS_PATH) and DEPS_PATH not in sys.path:
    sys.path.insert(0, DEPS_PATH)

from pypdf import PdfReader  # type: ignore
from sklearn.decomposition import NMF  # type: ignore
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer  # type: ignore
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore


STOPWORDS = set(ENGLISH_STOP_WORDS) | {
    "uh",
    "um",
    "yeah",
    "yes",
    "okay",
    "dont",
    "didnt",
    "thats",
    "interview",
    "densho",
    "repository",
    "digital",
    "segment",
    "says",
    "said",
    "yeah",
    "right",
    "kind",
    "used",
    "remember",
    "people",
    "going",
    "thought",
    "cause",
    "got",
    "thing",
    "lot",
    "guy",
    "really",
    "oh",
    "okay",
    "dad",
    "mom",
    "harry",
    "ken",
    "don",
    "gky",
    "2000",
    "ta",
    "rp",
    "tk",
    "sp",
    "ti",
    "nm",
    "hm",
}


class TranscriptHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_body = False
        self.current: List[str] = []
        self.paragraphs: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_map = dict(attrs)
        if tag == "div" and attrs_map.get("class") == "segmentBody":
            self.in_body = True
        if self.in_body and tag == "p":
            self.current = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_body and tag == "p":
            text = clean_whitespace(" ".join(self.current))
            if text:
                self.paragraphs.append(text)
            self.current = []
        if self.in_body and tag == "div":
            self.in_body = False

    def handle_data(self, data: str) -> None:
        if self.in_body:
            self.current.append(data)


@dataclass
class InterviewRecord:
    interview_id: str
    segment_id: str
    interviewee: str
    title: str
    year: int | None
    location: str
    generation: str
    topics: List[str]
    transcript_text: str
    transcript_paragraphs: List[str]
    word_count: int
    sentiment: float


def clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def parse_html_transcript(path: Path) -> List[str]:
    parser = TranscriptHTMLParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return [clean_transcript_line(p) for p in parser.paragraphs if clean_transcript_line(p)]


def parse_pdf_transcript(path: Path) -> List[str]:
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        chunks.append(text)
    text = "\n".join(chunks)
    paragraphs = [clean_transcript_line(chunk) for chunk in re.split(r"\n{2,}", text)]
    return [p for p in paragraphs if p]


def clean_transcript_line(value: str) -> str:
    value = clean_whitespace(value)
    if not value:
        return ""
    noisy_fragments = [
        "Densho Digital Archive",
        "Densho Digital Repository",
        "<Begin Segment",
        "Copyright",
    ]
    for fragment in noisy_fragments:
        value = value.replace(fragment, " ")
    value = re.sub(r"\bPage \d+\b", " ", value, flags=re.I)
    value = re.sub(r"^(?:[A-Z]{1,4}|Q|A):\s*", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) < 2:
        return ""
    return value


def extract_text(paths: Iterable[str]) -> tuple[str, List[str]]:
    paragraphs: List[str] = []
    for raw_path in sorted(paths):
        path = Path(raw_path)
        if path.suffix.lower() in {".htm", ".html"}:
            paragraphs.extend(parse_html_transcript(path))
        elif path.suffix.lower() == ".pdf":
            paragraphs.extend(parse_pdf_transcript(path))
        else:
            paragraphs.append(clean_transcript_line(path.read_text(encoding="utf-8", errors="replace")))
    paragraphs = [p for p in paragraphs if p]
    return "\n\n".join(paragraphs), paragraphs


def parse_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value or "")
    return int(match.group(0)) if match else None


def normalize_location(value: str) -> str:
    value = clean_whitespace(value)
    if not value:
        return "Unspecified"
    value = value.replace(" ,", ",")
    parts = [part.strip() for part in re.split(r"[;/]", value) if part.strip()]
    return parts[0] if parts else "Unspecified"


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    return [word for word in words if word not in STOPWORDS]


def excerpt_for_topic(paragraphs: List[str], keywords: List[str]) -> str:
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        if any(keyword in lowered for keyword in keywords):
            return paragraph[:280].strip()
    return paragraphs[0][:280].strip() if paragraphs else ""


def build_records(interviews_payload: dict) -> List[InterviewRecord]:
    analyzer = SentimentIntensityAnalyzer()
    records: List[InterviewRecord] = []
    for interview in interviews_payload["interviews"]:
        transcript_lookup = {item["local_path"]: item for item in interview.get("transcripts", [])}
        for raw_path in interview["raw_files"]:
            transcript_text, paragraphs = extract_text([raw_path])
            words = tokenize(transcript_text)
            if len(words) < 90:
                continue
            transcript_meta = transcript_lookup.get(raw_path, {})
            records.append(
                InterviewRecord(
                    interview_id=interview["interview_id"],
                    segment_id=transcript_meta.get("file_id", Path(raw_path).stem),
                    interviewee=interview["interviewee"],
                    title=transcript_meta.get("title") or interview["title"],
                    year=parse_year(interview.get("creation", "")),
                    location=normalize_location(interview.get("location", "")),
                    generation=interview.get("generation", "") or "Unspecified",
                    topics=interview.get("topics", []),
                    transcript_text=transcript_text,
                    transcript_paragraphs=paragraphs,
                    word_count=len(words),
                    sentiment=analyzer.polarity_scores(transcript_text)["compound"],
                )
            )
    if len(records) < 75:
        raise SystemExit(f"Only {len(records)} usable transcript segments after extraction; below the minimum threshold.")
    return records


def topic_model(records: List[InterviewRecord], topic_count: int = 6) -> tuple[list[dict], list[int], list[list[float]]]:
    documents = [record.transcript_text for record in records]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words=sorted(STOPWORDS),
        min_df=5,
        max_df=0.75,
        max_features=1800,
    )
    matrix = vectorizer.fit_transform(documents)
    actual_topics = max(3, min(topic_count, len(records) // 12))
    model = NMF(n_components=actual_topics, random_state=7, init="nndsvda", max_iter=500)
    doc_weights = model.fit_transform(matrix)
    feature_names = vectorizer.get_feature_names_out()
    dominant = doc_weights.argmax(axis=1).tolist()

    topic_rows = []
    for idx, component in enumerate(model.components_):
        top_indices = component.argsort()[-8:][::-1]
        keywords = [feature_names[i] for i in top_indices]
        member_indices = [i for i, topic_id in enumerate(dominant) if topic_id == idx]
        reps = sorted(member_indices, key=lambda i: doc_weights[i][idx], reverse=True)[:4]
        archive_topics = Counter()
        for i in member_indices:
            archive_topics.update(records[i].topics)
        top_archive_topics = [name for name, _count in archive_topics.most_common(2)]
        friendly_label = " / ".join(top_archive_topics) if top_archive_topics else ", ".join(keywords[:3])
        topic_rows.append(
            {
                "topic_id": idx,
                "label": friendly_label,
                "keywords": keywords,
                "archive_topics": top_archive_topics,
                "prevalence": len(member_indices),
                "share": round(len(member_indices) / len(records), 4),
                "avg_sentiment": round(mean(records[i].sentiment for i in member_indices), 3)
                if member_indices
                else 0.0,
                "representatives": [
                    {
                        "interview_id": records[i].interview_id,
                        "segment_id": records[i].segment_id,
                        "interviewee": records[i].interviewee,
                        "year": records[i].year,
                        "location": records[i].location,
                        "word_count": records[i].word_count,
                        "sentiment": round(records[i].sentiment, 3),
                        "excerpt": excerpt_for_topic(records[i].transcript_paragraphs, keywords[:4]),
                    }
                    for i in reps
                ],
            }
        )
    return topic_rows, dominant, doc_weights.tolist()


def main() -> int:
    base_dir = Path("data/oralhistorynlp")
    payload = json.loads((base_dir / "interviews_raw.json").read_text(encoding="utf-8"))
    records = build_records(payload)
    topics, dominant_topics, weights = topic_model(records)

    corpus_words = sum(record.word_count for record in records)
    years = [record.year for record in records if record.year]
    locations = Counter(record.location for record in records)
    top_terms = Counter()
    for record in records:
        top_terms.update(tokenize(record.transcript_text))

    location_rows = []
    for location, count in locations.most_common(12):
        matching = [record for record in records if record.location == location]
        location_rows.append(
            {
                "location": location,
                "count": count,
                "avg_sentiment": round(mean(item.sentiment for item in matching), 3),
                "avg_words": round(mean(item.word_count for item in matching), 1),
            }
        )

    year_rows = []
    year_counter = Counter(years)
    for year in sorted(year_counter):
        year_rows.append({"year": year, "count": year_counter[year]})

    sentiment_rows = [
        {
            "interview_id": record.interview_id,
            "segment_id": record.segment_id,
            "interviewee": record.interviewee,
            "sentiment": round(record.sentiment, 3),
            "word_count": record.word_count,
            "location": record.location,
            "year": record.year,
            "topic_id": dominant_topics[index],
        }
        for index, record in enumerate(records)
    ]

    interview_rows = []
    for index, record in enumerate(records):
        interview_rows.append(
            {
                "interview_id": record.interview_id,
                "segment_id": record.segment_id,
                "interviewee": record.interviewee,
                "title": record.title,
                "year": record.year or "",
                "location": record.location,
                "generation": record.generation,
                "word_count": record.word_count,
                "sentiment": round(record.sentiment, 3),
                "dominant_topic": dominant_topics[index],
                "topic_weight": round(max(weights[index]), 4),
            }
        )

    corpus_summary = {
        "sample_size": len(records),
        "unique_interviews": len({record.interview_id for record in records}),
        "total_words": corpus_words,
        "median_words": int(median(record.word_count for record in records)),
        "year_range": [min(years), max(years)] if years else [None, None],
        "unique_locations": len(locations),
        "source_manifest": "data/oralhistorynlp/sources_manifest.csv",
        "transcript_source_note": (
            "Public Densho oral history interview pages, narrator API records, and linked transcript files "
            "(mostly HTML segment transcripts, with some PDFs where Densho serves them that way)."
        ),
    }

    dashboard = {
        "summary": corpus_summary,
        "location_patterns": location_rows,
        "year_counts": year_rows,
        "topics": topics,
        "sentiment_rows": sentiment_rows,
        "top_terms": [{"term": term, "count": count} for term, count in top_terms.most_common(40)],
        "interviews": interview_rows,
        "method_notes": [
            "Discovery uses Densho's public narrator and entity API endpoints, then follows transcript file links exposed for each interview.",
            "Topic modeling uses TF-IDF plus non-negative matrix factorization (NMF), which is a practical topic baseline rather than a claim of exact method replication.",
            "Sentiment uses VADER compound scores at the transcript-segment level. Oral histories contain nuanced memories and quotations, so these scores should be treated as rough signals, not emotional truth.",
            "Locations come from Densho metadata fields and are normalized conservatively, usually to the first listed place string.",
            "This build analyzes public transcript segments linked from Densho interviews. It does not claim to reconstruct a larger closed corpus or a single-file transcript for every oral history.",
        ],
    }

    (base_dir / "dashboard-data.json").write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    (base_dir / "dashboard-data.js").write_text(
        "window.ORAL_HISTORY_NLP_DATA = " + json.dumps(dashboard, indent=2) + ";\n",
        encoding="utf-8",
    )

    with (base_dir / "interviews.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(interview_rows[0].keys()))
        writer.writeheader()
        writer.writerows(interview_rows)

    with (base_dir / "top_terms.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["term", "count"])
        writer.writeheader()
        writer.writerows(dashboard["top_terms"])

    with (base_dir / "topic_details.json").open("w", encoding="utf-8") as handle:
        json.dump({"topics": topics}, handle, indent=2)

    print(f"Usable transcripts: {len(records)}")
    print(f"Total words: {corpus_words}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
