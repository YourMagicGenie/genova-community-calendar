#!/usr/bin/env python3
"""Validate and map parser output into a review-only bulletin import payload."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

PARSER_VERSION = "1.0.0"
TIME_ZONE = ZoneInfo("Europe/Rome")
CATEGORY_KEYS = {
    "music", "theatre-performance", "art-exhibitions", "sports", "food-drink",
    "festivals-markets", "talks-workshops", "family", "outdoors-tours", "community-social",
}


def _https_url(value: str, field: str) -> str:
    parsed = urlsplit(value) if isinstance(value, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{field} must be an HTTPS URL")
    return value


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _local_timestamp(day_value: str, time_value: str) -> str | None:
    """Convert a supported Europe/Rome wall time, rejecting DST gaps/folds."""
    try:
        day = date.fromisoformat(day_value)
        clock = time.fromisoformat(time_value)
    except (TypeError, ValueError):
        return None
    naive = datetime.combine(day, clock)
    values = []
    for fold in (0, 1):
        aware = naive.replace(tzinfo=TIME_ZONE, fold=fold)
        round_trip = aware.astimezone(timezone.utc).astimezone(TIME_ZONE).replace(tzinfo=None)
        if round_trip == naive:
            values.append(aware)
    unique_offsets = {value.utcoffset() for value in values}
    if not values or len(unique_offsets) > 1:
        return None
    return values[0].isoformat(timespec="minutes")


def _category_suggestions(value) -> list[dict]:
    if not isinstance(value, list) or len(value) > 3:
        raise ValueError("category suggestions must be a list with at most three entries")
    output, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"category", "confidence", "evidence"}:
            raise ValueError("category suggestion has an invalid shape")
        category, confidence, evidence = item["category"], item["confidence"], item["evidence"]
        if category not in CATEGORY_KEYS or category in seen:
            raise ValueError("category suggestion key is invalid or repeated")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("category confidence must be between zero and one")
        if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 160:
            raise ValueError("category evidence must be short and nonempty")
        seen.add(category)
        output.append({"category": category, "confidence": confidence, "evidence": evidence})
    return output


def _candidate_occurrences(candidate: dict) -> list[tuple[str | None, str | None]]:
    listed = candidate.get("dates")
    if listed:
        if not isinstance(listed, list) or len(listed) > 31:
            raise ValueError("listed date values are invalid")
        return [(value, None) for value in listed]
    return [(candidate.get("start_date"), candidate.get("end_date"))]


def _map_one(candidate: dict, *, feed_id: int, bulletin_url: str, retrieved_at: str,
             occurrence_date: str | None, occurrence_end: str | None) -> dict | None:
    title = candidate.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    if candidate.get("review_status") != "needs_review":
        raise ValueError("PDF candidates must remain needs_review")
    page = candidate.get("source_page")
    bbox = candidate.get("source_bbox")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("candidate source page is invalid")
    if (not isinstance(bbox, list) or len(bbox) != 4
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in bbox)):
        raise ValueError("candidate source bounding box is invalid")
    field_evidence = candidate.get("field_evidence")
    if not isinstance(field_evidence, dict):
        raise ValueError("field-level evidence is required")
    evidence_bytes = json.dumps(field_evidence, ensure_ascii=False, separators=(",", ":")).encode()
    if len(evidence_bytes) > 8192:
        raise ValueError("field-level evidence exceeds the bounded size limit")
    unresolved = candidate.get("unresolved_reasons", [])
    if not isinstance(unresolved, list) or len(unresolved) > 12 or any(
        not isinstance(reason, str) or len(reason) > 160 for reason in unresolved
    ):
        raise ValueError("unresolved reasons must be short strings")

    suggestions = _category_suggestions(candidate.get("category_suggestions", []))
    precision = candidate.get("date_precision", "unknown")
    start_time = None
    reasons = list(unresolved)
    if occurrence_date and precision in {"day", "listed_dates"} and candidate.get("time"):
        start_time = _local_timestamp(occurrence_date, candidate["time"])
        if start_time is None:
            reasons.append("local time is invalid or ambiguous in Europe/Rome")
    elif occurrence_date and precision == "range" and candidate.get("time"):
        reasons.append("date range needs review before a single start time can be assigned")
    if occurrence_date and not candidate.get("time") and "start time not stated" not in reasons:
        reasons.append("start time not stated")

    identity = {
        "feed_id": feed_id,
        "bulletin_url": _canonical_url(bulletin_url),
        "page": page,
        "bbox": [round(float(value), 1) for value in bbox],
        "title": title.strip(),
        "date": occurrence_date,
        "end_date": occurrence_end,
        "time": candidate.get("time"),
    }
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    source_uid = "genova-bulletin:" + digest
    metadata = {
        "bulletin_url": bulletin_url,
        "retrieved_at": retrieved_at,
        "parser_version": PARSER_VERSION,
        "source_page": page,
        "source_bbox": [round(float(value), 1) for value in bbox],
        "field_evidence": field_evidence,
        "unresolved_reasons": list(dict.fromkeys(reasons)),
        "date_precision": precision,
        "start_date_candidate": occurrence_date,
        "end_date_candidate": occurrence_end,
        "partial_dates": candidate.get("partial_dates", []),
    }
    if len(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode()) > 16384:
        raise ValueError("source metadata exceeds the bounded size limit")
    return {
        "source_uid": source_uid,
        "title": title.strip()[:300],
        "start_time": start_time,
        "end_time": None,
        "normalized_url": bulletin_url,
        "location": candidate.get("venue"),
        "category_suggestions": suggestions,
        "field_evidence": field_evidence,
        "unresolved_reasons": metadata["unresolved_reasons"],
        "date_precision": precision,
        "source_page": page,
        "source_bbox": metadata["source_bbox"],
        "evidence_note": f"Monthly bulletin PDF · page {page} · verify extracted facts against the source.",
        "partial_dates": candidate.get("partial_dates", []),
        "start_date_candidate": occurrence_date,
        "end_date_candidate": occurrence_end,
    }


def prepare_import(source: dict, discovery: dict, candidates: list[dict]) -> dict:
    if (not isinstance(source, dict) or source.get("city") != "genova"
            or source.get("status") != "active" or isinstance(source.get("id"), bool)
            or not isinstance(source.get("id"), int) or source["id"] < 1):
        raise ValueError("a trusted active Genova source snapshot is required")
    source_page_url = _https_url(source.get("url"), "source page URL")
    if not isinstance(discovery, dict) or discovery.get("status") != "found":
        raise ValueError("only one unambiguous current bulletin candidate can be staged")
    if discovery.get("page_url") != source_page_url:
        raise ValueError("discovery page does not match the active source snapshot")
    bulletin_url = _https_url(discovery.get("pdf_url"), "bulletin PDF URL")
    retrieved_at = discovery.get("retrieval_timestamp")
    if not isinstance(retrieved_at, str):
        raise ValueError("discovery retrieval timestamp is required")
    try:
        parsed_timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("discovery retrieval timestamp is invalid") from exc
    if parsed_timestamp.tzinfo is None:
        raise ValueError("discovery retrieval timestamp must include a timezone")
    if not isinstance(candidates, list) or len(candidates) > 500:
        raise ValueError("parser candidate list is invalid or too large")
    events = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("parser candidate must be an object")
        for occurrence_date, occurrence_end in _candidate_occurrences(candidate):
            mapped = _map_one(
                candidate, feed_id=source["id"], bulletin_url=bulletin_url,
                retrieved_at=retrieved_at, occurrence_date=occurrence_date, occurrence_end=occurrence_end,
            )
            if mapped is not None:
                events.append(mapped)
    if len(events) > 500:
        raise ValueError("expanded parser candidate list is too large")
    uids = [event["source_uid"] for event in events]
    if len(set(uids)) != len(uids):
        raise ValueError("parser output contains duplicate candidate identities")
    return {
        "source": {"id": source["id"], "city": "genova", "status": "active", "url": source_page_url,
                   "name": str(source.get("name") or "Genova source")},
        "bulletin_url": bulletin_url,
        "retrieved_at": parsed_timestamp.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "parser_version": PARSER_VERSION,
        "events": events,
        "skipped_candidates": sum(not isinstance(candidate.get("title"), str) or not candidate.get("title", "").strip() for candidate in candidates),
    }


def validate_prepared(report: dict) -> None:
    if not isinstance(report, dict) or not isinstance(report.get("source"), dict):
        raise ValueError("prepared bulletin report is invalid")
    source = report["source"]
    if source.get("city") != "genova" or source.get("status") != "active":
        raise ValueError("prepared source is not an active Genova source")
    if isinstance(source.get("id"), bool) or not isinstance(source.get("id"), int) or source["id"] < 1:
        raise ValueError("prepared source ID is invalid")
    _https_url(source.get("url"), "source page URL")
    _https_url(report.get("bulletin_url"), "bulletin PDF URL")
    if report.get("parser_version") != PARSER_VERSION:
        raise ValueError("parser version mismatch")
    if not isinstance(report.get("events"), list) or len(report["events"]) > 500:
        raise ValueError("prepared event list is invalid")
    seen = set()
    for event in report["events"]:
        if not isinstance(event, dict):
            raise ValueError("prepared event candidate must be an object")
        if not event.get("source_uid", "").startswith("genova-bulletin:") or event["source_uid"] in seen:
            raise ValueError("candidate identity is missing or duplicated")
        seen.add(event["source_uid"])
        if event.get("normalized_url") != report["bulletin_url"]:
            raise ValueError("candidate normalized URL does not match report provenance")
        if event.get("start_time") is not None:
            parsed = datetime.fromisoformat(event["start_time"])
            if parsed.tzinfo is None:
                raise ValueError("event timestamps must include Europe/Rome offset")
        if not isinstance(event.get("field_evidence"), dict):
            raise ValueError("field-level evidence is required")
        if not isinstance(event.get("unresolved_reasons"), list) or not isinstance(event.get("partial_dates"), list):
            raise ValueError("partial and unresolved date evidence is invalid")
        metadata = {
            "bulletin_url": report["bulletin_url"], "retrieved_at": report["retrieved_at"],
            "parser_version": report["parser_version"], "source_page": event.get("source_page"),
            "source_bbox": event.get("source_bbox"), "field_evidence": event.get("field_evidence"),
            "unresolved_reasons": event.get("unresolved_reasons"), "date_precision": event.get("date_precision"),
            "start_date_candidate": event.get("start_date_candidate"),
            "end_date_candidate": event.get("end_date_candidate"), "partial_dates": event.get("partial_dates"),
        }
        if len(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode()) > 16384:
            raise ValueError("candidate metadata exceeds the bounded size limit")


def render_sql(report: dict) -> str:
    validate_prepared(report)
    encoded = base64.b64encode(json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode()).decode("ascii")
    return f"""\\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE _genova_bulletin_import(payload jsonb) ON COMMIT DROP;
INSERT INTO _genova_bulletin_import(payload)
VALUES (convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb);
SELECT public.import_genova_bulletin_facts(
  (payload #>> '{{source,id}}')::bigint,
  payload #>> '{{source,url}}',
  payload ->> 'bulletin_url',
  (payload ->> 'retrieved_at')::timestamptz,
  payload ->> 'parser_version',
  payload -> 'events'
) FROM _genova_bulletin_import;
COMMIT;
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="trusted source snapshot JSON")
    parser.add_argument("--discovery", type=Path, required=True, help="monthly PDF discovery JSON")
    parser.add_argument("--candidates", type=Path, required=True, help="offline parser output JSON")
    parser.add_argument("--output", type=Path, required=True, help="write a review-only SQL import script")
    args = parser.parse_args(argv)
    report = prepare_import(
        json.loads(args.source.read_text(encoding="utf-8")),
        json.loads(args.discovery.read_text(encoding="utf-8")),
        json.loads(args.candidates.read_text(encoding="utf-8")),
    )
    sql = render_sql(report)
    args.output.write_text(sql, encoding="utf-8")
    print(f"Prepared {len(report['events'])} needs-review event fact(s); skipped {report['skipped_candidates']} title-less candidate(s). No database write performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
