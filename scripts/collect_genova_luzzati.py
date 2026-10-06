#!/usr/bin/env python3
"""Bounded Giardini Luzzati index collector for the Genova pilot.

The collector fails closed unless the exact index URL is present as an active
Genova feed in Supabase. It checks robots.txt, makes at most one request to the
verified index, and emits only reviewable calendar facts plus access metadata.
It never fetches event detail pages and never writes to Supabase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.probe_giardini_luzzati import (
    MAX_CRAWL_DELAY_SECONDS,
    MAX_RESPONSE_BYTES,
    SOURCE_NAME,
    USER_AGENT,
    ProbeSkipped,
    _http_get,
    _robots_rules,
)

INDEX_URL = "https://www.spazio-comune.org/categoria-prodotto/eventi/"
PUBLISHER_URL = "https://www.spazio-comune.org/"
CITY = "genova"
TIME_ZONE = ZoneInfo("Europe/Rome")
PRODUCT_PATH_PREFIX = "/prodotto/"
MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})\b",
    re.I,
)
TIME_RE = re.compile(r"(?:\bore\s*|\bh\s*[:.]?\s*)([01]?\d|2[0-3])[:.]([0-5]\d)\b", re.I)
VENUE_RE = re.compile(r"Giardini\s+Luzzati(?:\s*[-–—]\s*Spazio\s+Comune|\s*\(Area\s+Archeologica\))?", re.I)


def _normalize_url(value: str) -> str:
    parsed = urlsplit(value)
    path = re.sub(r"/+$", "/", parsed.path or "/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _source_uid(feed_id: int, url: str, start_time: str | None) -> str:
    identity = f"{feed_id}|{_normalize_url(url)}|{start_time or 'unknown'}"
    return "genova-luzzati:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _load_public_config() -> tuple[str, str]:
    config = json.loads((REPO_ROOT / "xmlui" / "config.json").read_text(encoding="utf-8"))
    globals_ = config["appGlobals"]
    return globals_["supabaseUrl"].rstrip("/"), globals_["supabasePublishableKey"]


def load_active_source(url: str = INDEX_URL, opener=urllib.request.urlopen) -> dict:
    """Return the exact active source row or fail closed."""
    supabase_url, publishable_key = _load_public_config()
    query = urllib.parse.urlencode({
        "select": "id,city,url,name,status,feed_type,publisher_url,discovery_method",
        "city": f"eq.{CITY}",
        "url": f"eq.{url}",
        "status": "eq.active",
        "limit": "2",
    })
    request = urllib.request.Request(
        f"{supabase_url}/rest/v1/feeds?{query}",
        headers={"apikey": publishable_key, "user-agent": USER_AGENT},
    )
    try:
        with opener(request, timeout=20) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise ProbeSkipped("active source state could not be read") from error
    if not isinstance(rows, list) or len(rows) != 1:
        raise ProbeSkipped("exactly one active Giardini Luzzati source is required")
    source = rows[0]
    if (
        source.get("url") != url
        or source.get("city") != CITY
        or source.get("status") != "active"
        or source.get("feed_type") != "web_index"
    ):
        raise ProbeSkipped("source approval state did not match the fixed Genova web index")
    return source


class _ProductIndexParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.records: dict[str, dict] = {}
        self._card_depth = 0
        self._card_urls: list[str] = []
        self._card_text: list[str] = []
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._heading_url: str | None = None
        self._anchor_stack: list[str | None] = []

    @staticmethod
    def _attrs(attrs) -> dict:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag, attrs):
        values = self._attrs(attrs)
        classes = set(values.get("class", "").split())
        if tag == "li" and ("product" in classes or any(value.startswith("product") for value in classes)):
            self._card_depth = 1
            self._card_urls = []
            self._card_text = []
        elif self._card_depth:
            self._card_depth += 1

        href = None
        if tag == "a" and values.get("href"):
            candidate = urljoin(self.base_url, values["href"])
            parsed = urlsplit(candidate)
            if parsed.hostname == urlsplit(self.base_url).hostname and parsed.path.startswith(PRODUCT_PATH_PREFIX):
                href = _normalize_url(candidate)
                if self._card_depth:
                    self._card_urls.append(href)
            self._anchor_stack.append(href)

        if tag in {"h2", "h3", "h4"}:
            self._heading_depth = 1
            self._heading_text = []
            self._heading_url = next((value for value in reversed(self._anchor_stack) if value), None)
        elif self._heading_depth:
            self._heading_depth += 1

    def handle_endtag(self, tag):
        if self._heading_depth:
            self._heading_depth -= 1
            if self._heading_depth == 0:
                title = " ".join(" ".join(self._heading_text).split())
                if title:
                    url = self._heading_url
                    if not url and self._card_urls:
                        url = self._card_urls[-1]
                    if url:
                        record = self.records.setdefault(url, {"url": url, "title": title, "text": ""})
                        if not record.get("title"):
                            record["title"] = title
                self._heading_text = []
                self._heading_url = None

        if self._card_depth:
            self._card_depth -= 1
            if self._card_depth == 0:
                text = " ".join(" ".join(self._card_text).split())
                for url in dict.fromkeys(self._card_urls):
                    record = self.records.setdefault(url, {"url": url, "title": None, "text": ""})
                    if len(text) > len(record.get("text") or ""):
                        record["text"] = text
                self._card_urls = []
                self._card_text = []

        if tag == "a" and self._anchor_stack:
            self._anchor_stack.pop()

    def handle_data(self, data):
        clean = " ".join(data.split())
        if not clean:
            return
        if self._card_depth:
            self._card_text.append(clean)
        if self._heading_depth:
            self._heading_text.append(clean)


def parse_index(html: str, feed_id: int, publisher: str = SOURCE_NAME) -> list[dict]:
    parser = _ProductIndexParser(INDEX_URL)
    parser.feed(html)
    events: list[dict] = []
    for record in parser.records.values():
        title = (record.get("title") or "").strip()
        if not title:
            continue
        text = record.get("text") or ""
        date_match = DATE_RE.search(text)
        venue_match = VENUE_RE.search(text)
        venue = " ".join(venue_match.group(0).split()) if venue_match else None
        starts: list[str | None] = [None]
        if date_match:
            day = int(date_match.group(1))
            month = MONTHS[date_match.group(2).lower()]
            year = int(date_match.group(3))
            times = list(dict.fromkeys((int(h), int(m)) for h, m in TIME_RE.findall(text)))
            if times:
                starts = [
                    datetime(year, month, day, hour, minute, tzinfo=TIME_ZONE).isoformat()
                    for hour, minute in times
                ]
        for start_time in starts:
            normalized_url = _normalize_url(record["url"])
            events.append({
                "feed_id": feed_id,
                "title": title,
                "start_time": start_time,
                "end_time": None,
                "location": venue,
                "publisher": publisher,
                "url": record["url"],
                "normalized_url": normalized_url,
                "source_uid": _source_uid(feed_id, normalized_url, start_time),
                "category": None,
                "category_confidence": None,
                "review_status": "needs_review",
            })
    return events


def collect(source_loader=load_active_source, get=_http_get, sleeper=time.sleep) -> dict:
    source = source_loader(INDEX_URL)
    request_count = 0

    def tracked_get(url: str):
        nonlocal request_count
        request_count += 1
        return get(url)

    robots, crawl_delay, robots_status = _robots_rules(INDEX_URL, get=tracked_get)
    if robots is not None and not robots.can_fetch(USER_AGENT, INDEX_URL):
        raise ProbeSkipped("robots.txt disallows the active source index")
    if crawl_delay > MAX_CRAWL_DELAY_SECONDS:
        raise ProbeSkipped("published crawl delay exceeds the collector wait limit")
    if crawl_delay:
        sleeper(crawl_delay)

    response = tracked_get(INDEX_URL)
    if response.status != 200:
        raise ProbeSkipped(f"event index returned HTTP {response.status}")
    if urlsplit(response.url).hostname != urlsplit(INDEX_URL).hostname:
        raise ProbeSkipped("event index redirected to another host")
    body = response.read()
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProbeSkipped("event index exceeded the response-size limit")
    events = parse_index(body.decode("utf-8", errors="replace"), int(source["id"]), source.get("name") or SOURCE_NAME)
    return {
        "status": "ok",
        "source": {
            "id": int(source["id"]),
            "name": source.get("name") or SOURCE_NAME,
            "url": INDEX_URL,
            "publisher_url": source.get("publisher_url") or PUBLISHER_URL,
        },
        "access": {
            "robots_http_status": robots_status,
            "robots_decision": "allowed" if robots is not None else "missing_no_rules",
            "page_http_status": response.status,
            "request_count": request_count,
            "crawl_delay_seconds": crawl_delay,
        },
        "events": events,
        "events_found": len(events),
        "events_needing_review": sum(event["review_status"] == "needs_review" for event in events),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="write the facts-only report to this JSON file")
    args = parser.parse_args()
    try:
        report = collect()
    except ProbeSkipped as error:
        print(json.dumps({"status": "skipped", "reason": str(error)}, sort_keys=True))
        return 2
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
