#!/usr/bin/env python3
"""Bounded Giardini Luzzati index collector for the Genova pilot.

The collector fails closed unless the exact index URL is present as an active
Genova feed in Supabase. It checks robots.txt, makes at most one request to the
verified index, and emits only reviewable calendar facts plus access metadata.
It fetches only a configurable number of sequential same-host event detail
pages after the index, and never writes to Supabase or retains page content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
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
MAX_DETAIL_PAGES = 12
DEFAULT_DETAIL_PAGE_LIMIT = 2
CATEGORY_ALIASES = {
    "music": "music", "musica": "music", "concerti": "music",
    "theatre": "theatre-performance", "theater": "theatre-performance",
    "teatro": "theatre-performance", "performance": "theatre-performance",
    "art": "art-exhibitions", "arte": "art-exhibitions", "mostre": "art-exhibitions",
    "sport": "sports", "sports": "sports", "food": "food-drink", "food & drink": "food-drink",
    "festival": "festivals-markets", "festivals": "festivals-markets", "mercati": "festivals-markets",
    "talks": "talks-workshops", "workshops": "talks-workshops", "laboratori": "talks-workshops",
    "family": "family", "famiglie": "family", "bambini": "family",
    "outdoors": "outdoors-tours", "tours": "outdoors-tours",
    "community": "community-social", "comunità": "community-social",
}
DETAIL_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})\b",
    re.I,
)
CATEGORY_LINE_RE = re.compile(r"(?:categoria|category)\s*[:：]\s*([^|.;\n]+)", re.I)
CATEGORY_KEYWORDS = {
    "music": ("musica", "musicale", "concerto", "concerti", "jazz", "dj set", "live music"),
    "theatre-performance": ("teatro", "spettacolo", "performance", "danza", "cabaret", "commedia"),
    "art-exhibitions": ("mostra", "mostre", "esposizione", "arte", "fotografia", "cinema", "film"),
    "sports": ("sport", "partita", "torneo", "fitness", "allenamento", "gara"),
    "food-drink": ("degustazione", "cucina", "vino", "birra", "aperitivo", "cena", "street food"),
    "festivals-markets": ("festival", "mercato", "mercatino", "fiera", "sagra"),
    "talks-workshops": ("laboratorio", "workshop", "corso", "conferenza", "presentazione", "poesia", "lettura"),
    "family": ("bambini", "famiglie", "per bambini", "family", "kids"),
    "outdoors-tours": ("escursione", "trekking", "passeggiata", "visita guidata", "tour", "natura"),
    "community-social": ("comunita", "sociale", "incontro", "giochi", "socialita"),
}
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
                "evidence_note": "date_time=index_card" if start_time else "index_card_checked; date_time=unknown",
            })
    if diagnostics is not None:
        diagnostics.update(counts)
    return events


class _DetailParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.jsonld = []
        self.text = []
        self.h1 = []
        self.skip = 0
        self.script_type = ""
        self.script_data = []
        self.in_h1 = False
        self.h1_data = []
        self.scope_tags = []
        self.scoped_text = []

    def handle_starttag(self, tag, attrs):
        attrs = {k.casefold(): v or "" for k, v in attrs}
        tag = tag.casefold()
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1
            if tag == "script":
                self.script_type = attrs.get("type", "").casefold()
                self.script_data = []
            return
        if self.skip:
            return
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").casefold()
            if key and attrs.get("content"):
                self.meta.setdefault(key, []).append(attrs["content"].strip())
        classes = set(attrs.get("class", "").casefold().split())
        if tag in {"main", "article"} or classes.intersection({"product", "summary", "entry-summary", "product-summary"}):
            self.scope_tags.append(tag)
        if tag in {"address", "article", "br", "div", "h1", "h2", "h3", "li", "main", "p", "section"}:
            self.text.append("\n")
            if self.scope_tags:
                self.scoped_text.append("\n")
        if tag == "h1":
            self.in_h1, self.h1_data = True, []

    def handle_endtag(self, tag):
        tag = tag.casefold()
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1
            if tag == "script" and self.script_type == "application/ld+json":
                self.jsonld.append("".join(self.script_data))
            self.script_type, self.script_data = "", []
        elif tag == "h1" and self.in_h1:
            value = " ".join(" ".join(self.h1_data).split())
            if value:
                self.h1.append(value)
            self.in_h1, self.h1_data = False, []
        if tag in {"address", "article", "br", "div", "h1", "h2", "h3", "li", "main", "p", "section"}:
            self.text.append("\n")
            if self.scope_tags:
                self.scoped_text.append("\n")
        for index in range(len(self.scope_tags) - 1, -1, -1):
            if self.scope_tags[index] == tag:
                del self.scope_tags[index:]
                break

    def handle_data(self, data):
        if self.skip:
            if self.script_type == "application/ld+json":
                self.script_data.append(data)
            return
        clean = " ".join(data.split())
        if clean:
            self.text.append(clean)
            if self.scope_tags:
                self.scoped_text.append(clean)
            if self.in_h1:
                self.h1_data.append(clean)


def _jsonld_events(value):
    if isinstance(value, list):
        for item in value:
            yield from _jsonld_events(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _jsonld_events(value["@graph"])


def _category(value):
    if isinstance(value, list):
        for item in value:
            result = _category(item)
            if result[0]:
                return result
        return None, None
    if isinstance(value, dict):
        return _category(value.get("name") or value.get("@value"))
    if isinstance(value, str):
        label = value.strip().casefold()
        key = CATEGORY_ALIASES.get(label)
        if key:
            return key, 0.95
        for part in re.split(r"[,;|]", label):
            key = CATEGORY_ALIASES.get(part.strip())
            if key:
                return key, 0.95
        return None, None
    return None, None


def _fold_text(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _infer_category(title, description):
    """Conservative Italian/English keyword classification from source wording."""
    title_text, description_text = _fold_text(title or ""), _fold_text(description or "")
    scores = {}
    title_hits = set()
    for category, phrases in CATEGORY_KEYWORDS.items():
        for phrase in phrases:
            needle = _fold_text(phrase)
            pattern = re.compile(r"(?<!\\w)" + re.escape(needle) + r"(?!\\w)")
            if pattern.search(title_text):
                scores[category] = scores.get(category, 0) + 3
                title_hits.add(category)
            if pattern.search(description_text):
                scores[category] = scores.get(category, 0) + 1
    if not scores:
        return None, None
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None, None
    category = ranked[0][0]
    return category, (0.82 if category in title_hits else 0.76)


def _metadata_time(value):
    if not isinstance(value, str):
        return None
    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if "T" not in raw and " " not in raw:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TIME_ZONE)
    else:
        parsed = parsed.astimezone(TIME_ZONE)
    return parsed.isoformat()


def parse_detail(html: str, index_event: dict, feed_id: int) -> list[dict]:
    parser = _DetailParser()
    parser.feed(html)
    scoped_text = " ".join(parser.scoped_text)
    page_text = " ".join(parser.text)
    # Some publisher templates put the event date/venue in a sibling widget,
    # outside the WooCommerce summary. Use the full visible page when the
    # scoped summary does not contain both date and time evidence.
    scoped_has_date = bool(DETAIL_DATE_RE.search(scoped_text))
    scoped_has_time = bool(TIME_RE.search(scoped_text))
    text = scoped_text if scoped_has_date and scoped_has_time else page_text
    facts = []
    for raw in parser.jsonld:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for node in _jsonld_events(data):
            start = _metadata_time(node.get("startDate") or node.get("start_time"))
            if not start:
                continue
            end = _metadata_time(node.get("endDate") or node.get("end_time"))
            location = node.get("location")
            if isinstance(location, dict):
                location = location.get("name")
            if isinstance(location, list):
                location = location[0] if len(location) == 1 and isinstance(location[0], str) else None
            category, confidence = _category(node.get("category") or node.get("keywords"))
            facts.append((start, end, location if isinstance(location, str) else None, category, confidence, "structured_event_metadata"))
    meta = parser.meta
    def meta_first(*names):
        for name in names:
            values = meta.get(name.casefold(), [])
            if values:
                return values[0]
        return None
    meta_start = _metadata_time(meta_first("event:start_time", "event:start_date", "startdate", "startdatetime", "start_time"))
    meta_end = _metadata_time(meta_first("event:end_time", "event:end_date", "enddate", "enddatetime", "end_time"))
    meta_location = meta_first("event:location", "location", "place:location")
    meta_category, meta_confidence = _category(meta_first("article:section", "category", "keywords"))
    if not facts and meta_start:
        facts.append((meta_start, meta_end, meta_location, meta_category, meta_confidence, "page_metadata"))
    if not facts:
        dates = []
        for match in DETAIL_DATE_RE.finditer(text):
            try:
                value = (int(match.group(3)), MONTHS[match.group(2).casefold()], int(match.group(1)))
                datetime(*value)
                if value not in dates:
                    dates.append(value)
            except ValueError:
                continue
        times = list(dict.fromkeys((int(h), int(m)) for h, m in TIME_RE.findall(text)))
        if len(dates) == 1 and times:
            year, month, day = dates[0]
            facts = [
                (datetime(year, month, day, h, m, tzinfo=TIME_ZONE).isoformat(), None, None, None, None, "visible_event_text")
                for h, m in times
            ]
    venue_match = VENUE_RE.search(text)
    venue = " ".join(venue_match.group(0).split()) if venue_match else meta_location
    category_match = CATEGORY_LINE_RE.search(text)
    explicit_category, explicit_confidence = _category(category_match.group(1)) if category_match else (meta_category, meta_confidence)
    if explicit_category and category_match:
        explicit_confidence = 0.85
    category_evidence = (
        "source_category_label" if category_match
        else "category_metadata" if meta_category
        else None
    )
    if not explicit_category:
        description_parts = (
            parser.meta.get("description", [])
            + parser.meta.get("og:description", [])
            + parser.scoped_text
            + parser.text
        )
        explicit_category, explicit_confidence = _infer_category(
            next(iter(parser.h1), None) or index_event["title"],
            " ".join(description_parts),
        )
        if explicit_category:
            category_evidence = "title_or_description_keywords"
    if not facts:
        facts = [(None, None, None, None, None, None)]
    output = []
    title = next(iter(parser.h1), None) or index_event["title"]
    seen_starts = set()
    for start, end, location, category, confidence, source in facts:
        if start in seen_starts:
            continue
        seen_starts.add(start)
        location = location or venue
        category = category or explicit_category
        confidence = confidence or explicit_confidence
        evidence = []
        if source:
            evidence.append(f"date_time={source}")
        if location:
            evidence.append("location=event_metadata_or_visible_text")
        if category:
            evidence.append(f"category={category_evidence or 'event_metadata'}")
        output.append({
            "feed_id": feed_id, "title": title, "start_time": start, "end_time": end,
            "location": location, "publisher": index_event["publisher"],
            "url": index_event["url"], "normalized_url": index_event["normalized_url"],
            "source_uid": _source_uid(feed_id, index_event["normalized_url"], start),
            "category": category, "category_confidence": confidence,
            "review_status": "needs_review",
            "evidence_note": "; ".join(evidence) or "detail_page_checked; facts not explicit",
        })
    return output


def collect(source: dict, get=_http_get, sleeper=time.sleep, detail_page_limit=DEFAULT_DETAIL_PAGE_LIMIT) -> dict:
    source = validate_active_source(source, INDEX_URL)
    if isinstance(detail_page_limit, bool) or not isinstance(detail_page_limit, int) or not 0 <= detail_page_limit <= MAX_DETAIL_PAGES:
        raise ProbeSkipped(f"detail-page limit must be an integer between 0 and {MAX_DETAIL_PAGES}")
    request_count = 0

    def tracked_get(url):
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
    if response.status == 429:
        raise ProbeSkipped("event index rate-limited the collector")
    if response.status != 200:
        raise ProbeSkipped(f"event index returned HTTP {response.status}")
    host = (urlsplit(INDEX_URL).hostname or "").casefold()
    if (urlsplit(response.url).hostname or "").casefold() != host:
        raise ProbeSkipped("event index redirected to another host")
    body = response.read()
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProbeSkipped("event index exceeded the response-size limit")
    diagnostics = {}
    events = parse_index(body.decode("utf-8", errors="replace"), int(source["id"]), source.get("name") or SOURCE_NAME, diagnostics=diagnostics)
    candidates = list({event["normalized_url"]: event for event in events}.values())[:detail_page_limit]
    detail_pages_checked = 0
    for index_event in candidates:
        target = index_event["url"]
        parsed = urlsplit(target)
        if parsed.scheme.casefold() != "https" or (parsed.hostname or "").casefold() != host or not parsed.path.startswith(PRODUCT_PATH_PREFIX):
            continue
        if robots is not None and not robots.can_fetch(USER_AGENT, target):
            raise ProbeSkipped("robots.txt disallows a candidate event detail path")
        if crawl_delay:
            sleeper(crawl_delay)
        detail = tracked_get(target)
        if detail.status == 429:
            raise ProbeSkipped("event detail page rate-limited the collector")
        if detail.status != 200:
            raise ProbeSkipped(f"event detail page returned HTTP {detail.status}")
        if (urlsplit(detail.url).hostname or "").casefold() != host:
            raise ProbeSkipped("event detail page redirected to another host")
        detail_body = detail.read()
        if len(detail_body) > MAX_RESPONSE_BYTES:
            raise ProbeSkipped("event detail page exceeded the response-size limit")
        detail_pages_checked += 1
        enriched = parse_detail(detail_body.decode("utf-8", errors="replace"), index_event, int(source["id"]))
        old = [event for event in events if event["normalized_url"] == index_event["normalized_url"]]
        if any(event["start_time"] for event in enriched):
            old = [event for event in events if event["normalized_url"] == index_event["normalized_url"]]
            for event in enriched:
                if not event["location"]:
                    event["location"] = next((row["location"] for row in old if row.get("location")), None)
                if not event["category"]:
                    event["category"] = next((row["category"] for row in old if row.get("category")), None)
                    event["category_confidence"] = next((row["category_confidence"] for row in old if row.get("category_confidence") is not None), None)
            events = [event for event in events if event["normalized_url"] != index_event["normalized_url"]]
            events.extend(enriched)
        else:
            for event in old:
                for key in ("location", "category", "category_confidence", "evidence_note"):
                    value = next((row.get(key) for row in enriched if row.get(key)), None)
                    if value:
                        event[key] = value
    diagnostics["detail_pages_checked"] = detail_pages_checked
    return {
        "status": "ok",
        "source": {"id": int(source["id"]), "name": source.get("name") or SOURCE_NAME, "url": INDEX_URL, "publisher_url": source.get("publisher_url") or PUBLISHER_URL},
        "access": {
            "robots_http_status": robots_status, "robots_decision": "allowed" if robots is not None else "missing_no_rules",
            "page_http_status": response.status, "request_count": request_count,
            "crawl_delay_seconds": crawl_delay, "detail_page_limit": detail_page_limit,
            "detail_pages_checked": detail_pages_checked,
        },
        "diagnostics": diagnostics, "events": events, "events_found": len(events),
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
    parser.add_argument("--detail-page-limit", type=int, default=DEFAULT_DETAIL_PAGE_LIMIT,
                        help=f"sequential detail pages to request (0-{MAX_DETAIL_PAGES})")
    args = parser.parse_args()
    try:
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(json.dumps({"status": "skipped", "reason": "approved source snapshot could not be read"}, sort_keys=True))
        return 2
    try:
        report = collect(source, detail_page_limit=args.detail_page_limit)
    except ProbeSkipped as error:
        print(json.dumps({"status": "skipped", "reason": str(error)}, sort_keys=True))
        return 2
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "events_found": report["events_found"],
        "events_needing_review": report["events_needing_review"],
        "request_count": report["access"]["request_count"],
        "detail_page_limit": report["access"]["detail_page_limit"],
        "detail_pages_checked": report["access"]["detail_pages_checked"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
