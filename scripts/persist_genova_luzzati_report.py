#!/usr/bin/env python3
"""Validate a bounded Luzzati collector report and render one transactional SQL import.

The generated SQL only upserts reviewable facts and appends scan provenance.
It never deletes prior facts and never publishes an event.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

INDEX_URL = "https://www.spazio-comune.org/categoria-prodotto/eventi/"
HOST = "www.spazio-comune.org"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EVENT_FIELDS = {
    "feed_id", "title", "start_time", "end_time", "location", "publisher", "url",
    "normalized_url", "source_uid", "category", "category_confidence", "review_status",
}


def _iso_or_none(value, field):
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp or null")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone offset")


def validate_report(report: dict) -> None:
    if not isinstance(report, dict) or report.get("status") != "ok":
        raise ValueError("only a successful collector report can be persisted")
    source = report.get("source")
    access = report.get("access")
    events = report.get("events")
    if not isinstance(source, dict) or source.get("url") != INDEX_URL:
        raise ValueError("report source is not the fixed Luzzati index")
    if not isinstance(source.get("id"), int) or source["id"] < 1:
        raise ValueError("report source ID is invalid")
    if not isinstance(access, dict):
        raise ValueError("report access metadata is missing")
    if access.get("robots_decision") not in {"allowed", "missing_no_rules"}:
        raise ValueError("a blocked or unavailable source report cannot persist event facts")
    request_count = access.get("request_count")
    if not isinstance(request_count, int) or not 1 <= request_count <= 2:
        raise ValueError("report request count violates the bounded pilot")
    if not isinstance(events, list) or len(events) > 500:
        raise ValueError("report event list is invalid or unexpectedly large")

    seen = set()
    for event in events:
        if not isinstance(event, dict) or set(event) - EVENT_FIELDS:
            raise ValueError("event contains fields outside the facts-only contract")
        if event.get("feed_id") != source["id"]:
            raise ValueError("event feed ID does not match the approved source")
        if not isinstance(event.get("title"), str) or not event["title"].strip():
            raise ValueError("event title is required")
        if event.get("review_status") != "needs_review":
            raise ValueError("collector output must enter review as needs_review")
        for key in ("url", "normalized_url"):
            value = event.get(key)
            parsed = urlsplit(value) if isinstance(value, str) else None
            if not parsed or parsed.scheme != "https" or parsed.hostname != HOST:
                raise ValueError(f"event {key} must stay on the approved publisher host")
        source_uid = event.get("source_uid")
        if not isinstance(source_uid, str) or not source_uid.startswith("genova-luzzati:"):
            raise ValueError("event source UID is invalid")
        if source_uid in seen:
            raise ValueError("report contains a duplicate source UID")
        seen.add(source_uid)
        _iso_or_none(event.get("start_time"), "start_time")
        _iso_or_none(event.get("end_time"), "end_time")
        confidence = event.get("category_confidence")
        if confidence is not None and (not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
            raise ValueError("category confidence must be between zero and one")


def render_sql(report: dict, revision: str) -> str:
    validate_report(report)
    if not SHA_RE.fullmatch(revision):
        raise ValueError("collector revision must be a full Git commit SHA")
    encoded = base64.b64encode(
        json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"""\\set ON_ERROR_STOP on
BEGIN;

CREATE TEMP TABLE _genova_luzzati_report(payload jsonb) ON COMMIT DROP;
INSERT INTO _genova_luzzati_report(payload)
VALUES (convert_from(decode('{encoded}', 'base64'), 'UTF8')::jsonb);

INSERT INTO public.genova_source_scans (
  feed_id, collector_revision, requested_url, robots_decision,
  robots_http_status, page_http_status, request_count, outcome,
  events_found, finished_at
)
SELECT
  (payload #>> '{{source,id}}')::bigint,
  '{revision}',
  payload #>> '{{source,url}}',
  payload #>> '{{access,robots_decision}}',
  NULLIF(payload #>> '{{access,robots_http_status}}', '')::integer,
  NULLIF(payload #>> '{{access,page_http_status}}', '')::integer,
  (payload #>> '{{access,request_count}}')::integer,
  'succeeded',
  COALESCE((payload ->> 'events_found')::integer, jsonb_array_length(payload -> 'events')),
  now()
FROM _genova_luzzati_report;

INSERT INTO public.genova_event_facts (
  feed_id, source_uid, title, start_time, end_time, location,
  publisher_label, direct_url, normalized_url, category,
  category_confidence, review_status, evidence_note, first_seen, last_seen
)
SELECT
  (event ->> 'feed_id')::bigint,
  event ->> 'source_uid',
  event ->> 'title',
  NULLIF(event ->> 'start_time', '')::timestamptz,
  NULLIF(event ->> 'end_time', '')::timestamptz,
  NULLIF(event ->> 'location', ''),
  event ->> 'publisher',
  event ->> 'url',
  event ->> 'normalized_url',
  NULLIF(event ->> 'category', ''),
  NULLIF(event ->> 'category_confidence', '')::numeric,
  'needs_review',
  'Giardini Luzzati public event index; collector revision {revision}',
  now(),
  now()
FROM _genova_luzzati_report,
LATERAL jsonb_array_elements(payload -> 'events') AS event
ON CONFLICT (source_uid) DO UPDATE SET
  title = EXCLUDED.title,
  start_time = EXCLUDED.start_time,
  end_time = EXCLUDED.end_time,
  location = EXCLUDED.location,
  publisher_label = EXCLUDED.publisher_label,
  direct_url = EXCLUDED.direct_url,
  category = EXCLUDED.category,
  category_confidence = EXCLUDED.category_confidence,
  last_seen = now(),
  evidence_note = EXCLUDED.evidence_note
WHERE public.genova_event_facts.feed_id = EXCLUDED.feed_id
  AND public.genova_event_facts.normalized_url = EXCLUDED.normalized_url;

COMMIT;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    sql = render_sql(report, args.revision)
    Path(args.output).write_text(sql, encoding="utf-8")
    print(f"Validated {len(report['events'])} reviewable event occurrence(s); persistence SQL rendered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
