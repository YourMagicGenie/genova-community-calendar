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


def validate_active_source(source: dict, url: str = INDEX_URL) -> dict:
    """Validate the trusted source snapshot supplied by the guarded workflow."""
    if not isinstance(source, dict):
        raise ProbeSkipped("approved source snapshot is invalid")
    if (
        source.get("url") != url
        or source.get("city") != CITY
        or source.get("status") != "active"
        or source.get("feed_type") != "web_index"
        or not isinstance(source.get("id"), int)
        or source["id"] < 1
    ):
        raise ProbeSkipped("source approval state did not match the fixed Genova web index")
    return source


class _Element:
    """Small transient DOM node; source markup is never returned or persisted."""

    def __init__(self, tag: str, attrs: dict, parent: "_Element | None" = None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[_Element] = []
        self.text_parts: list[str] = []

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


class _ProductIndexParser(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg"}
    CONTAINER_TAGS = {"article", "div", "li", "section", "ul"}
    GENERIC_TITLES = {"read more", "leggi", "scopri di più", "dettagli"}

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.host = (urlsplit(base_url).hostname or "").casefold()
        self.root = _Element("document", {})
        self.stack = [self.root]
        self.ignored: list[str] = []
        self.product_links: list[tuple[_Element, str]] = []
        self.url_sets: dict[_Element, set[str]] = {}

    @staticmethod
    def _attrs(attrs) -> dict:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag, attrs):
        tag = tag.casefold()
        if self.ignored:
            if tag in self.SKIP_TAGS:
                self.ignored.append(tag)
            return
        if tag in self.SKIP_TAGS:
            self.ignored.append(tag)
            return

        # Repair common optional-end-tag cases so one malformed card cannot
        # accidentally absorb every later event card.
        if tag in {"li", "p", "a"}:
            for index in range(len(self.stack) - 1, 0, -1):
                if self.stack[index].tag == tag:
                    del self.stack[index:]
                    break

        node = _Element(tag, self._attrs(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag == "a" and node.attrs.get("href"):
            candidate = urljoin(self.base_url, node.attrs["href"])
            parsed = urlsplit(candidate)
            if (
                parsed.scheme.casefold() == "https"
                and (parsed.hostname or "").casefold() == self.host
                and parsed.path.startswith(PRODUCT_PATH_PREFIX)
            ):
                self.product_links.append((node, _normalize_url(candidate)))
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in self.VOID_TAGS and not self.ignored:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if self.ignored:
            for index in range(len(self.ignored) - 1, -1, -1):
                if self.ignored[index] == tag:
                    del self.ignored[index:]
                    break
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not self.ignored and self.stack:
            clean = " ".join(data.split())
            if clean:
                self.stack[-1].text_parts.append(clean)

    @staticmethod
    def _text(node: _Element) -> str:
        return " ".join(
            part
            for current in node.walk()
            for part in current.text_parts
        ).strip()

    def _urls_in(self, node: _Element) -> set[str]:
        return self.url_sets.get(node, set())

    @staticmethod
    def _ancestors(node: _Element):
        current = node
        while current is not None:
            yield current
            current = current.parent

    @staticmethod
    def _is_card(node: _Element) -> bool:
        classes = set(node.attrs.get("class", "").casefold().split())
        product_class = any(
            token in {"product", "type-product", "event", "event-card", "event-item"}
            or token.startswith(("product-", "event-"))
            or token == "woocommerce-loop-product"
            for token in classes
        )
        return node.tag == "article" or product_class or (
            node.tag == "li" and ("product" in classes or "type-product" in classes)
        )

    def _container_for(self, link: _Element, url: str) -> _Element:
        ancestors = list(self._ancestors(link))
        for node in ancestors[1:]:
            if self._is_card(node) and self._urls_in(node) == {url}:
                return node

        # Themes do not always label cards. Use the broadest nearby common
        # container that has only this distinct product URL; stop at a grid
        # containing links to multiple products.
        best = link
        for node in ancestors[1:]:
            if node.tag not in self.CONTAINER_TAGS:
                continue
            urls = self._urls_in(node)
            if urls == {url}:
                best = node
            elif urls:
                break
        return best

    def records(self) -> tuple[list[dict], dict]:
        links_by_url: dict[str, list[_Element]] = {}
        for link, url in self.product_links:
            links_by_url.setdefault(url, []).append(link)
            for ancestor in self._ancestors(link):
                self.url_sets.setdefault(ancestor, set()).add(url)

        records = []
        for url, links in links_by_url.items():
            containers = [self._container_for(link, url) for link in links]
            container = max(containers, key=lambda node: len(self._text(node)))
            headings = [
                self._text(node)
                for node in container.walk()
                if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
                and self._text(node)
            ]
            linked_titles = [self._text(link) for link in links if self._text(link)]
            title = next(iter(headings), None) or max(linked_titles, key=len, default=None)
            if title and title.casefold() in self.GENERIC_TITLES:
                title = None
            records.append({"url": url, "title": title, "text": self._text(container)})

        diagnostics = {
            "same_host_product_links": len(self.product_links),
            "distinct_candidate_urls": len(links_by_url),
            "candidate_records": len(records),
            "records_with_titles": sum(bool(record["title"]) for record in records),
            "records_with_dates": 0,
            "records_with_times": 0,
        }
        return records, diagnostics


def parse_index(
    html: str,
    feed_id: int,
    publisher: str = SOURCE_NAME,
    diagnostics: dict | None = None,
) -> list[dict]:
    parser = _ProductIndexParser(INDEX_URL)
    parser.feed(html)
    records, counts = parser.records()
    events: list[dict] = []
    for record in records:
        title = (record.get("title") or "").strip()
        text = record.get("text") or ""
        date_match = DATE_RE.search(text)
        times = list(dict.fromkeys((int(h), int(m)) for h, m in TIME_RE.findall(text)))
        counts["records_with_dates"] += bool(date_match)
        counts["records_with_times"] += bool(times)
        if not title:
            continue
        venue_match = VENUE_RE.search(text)
        venue = " ".join(venue_match.group(0).split()) if venue_match else None
        starts: list[str | None] = [None]
        if date_match:
            day = int(date_match.group(1))
            month = MONTHS[date_match.group(2).lower()]
            year = int(date_match.group(3))
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
    if diagnostics is not None:
        diagnostics.update(counts)
    return events


def collect(source: dict, get=_http_get, sleeper=time.sleep) -> dict:
    source = validate_active_source(source, INDEX_URL)
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
    diagnostics = {}
    events = parse_index(
        body.decode("utf-8", errors="replace"),
        int(source["id"]),
        source.get("name") or SOURCE_NAME,
        diagnostics=diagnostics,
    )
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
        "diagnostics": diagnostics,
        "events": events,
        "events_found": len(events),
        "events_needing_review": sum(event["review_status"] == "needs_review" for event in events),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        required=True,
        help="trusted JSON source snapshot produced by the guarded pilot workflow",
    )
    parser.add_argument("--output", help="write the facts-only report to this JSON file")
    args = parser.parse_args()
    try:
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(json.dumps({"status": "skipped", "reason": "approved source snapshot could not be read"}, sort_keys=True))
        return 2
    try:
        report = collect(source)
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
