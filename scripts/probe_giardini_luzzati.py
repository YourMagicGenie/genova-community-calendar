#!/usr/bin/env python3
"""One-page, read-only probe for the first Giardini Luzzati event.

Checks robots.txt before making exactly one request to the fixed public event URL.
Prints only calendar facts; never stores or prints the source HTML.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

SOURCE_NAME = "Giardini Luzzati / Spazio Comune"
EVENT_URL = "https://www.spazio-comune.org/prodotto/nessuno-ci-insegna-a-cadere/"
USER_AGENT = "GenovaCommunityCalendarProbe/0.1 (+https://github.com/YourMagicGenie/genova-community-calendar)"
MAX_RESPONSE_BYTES = 2_000_000
MAX_CRAWL_DELAY_SECONDS = 120
ROME = ZoneInfo("Europe/Rome")
MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


class ProbeSkipped(Exception):
    """The requested page should not be fetched in this run."""

    def __init__(self, message: str, *, report: dict | None = None):
        super().__init__(message)
        self.report = report or {}


class _Response:
    def __init__(self, status: int, url: str, body: bytes):
        self.status = status
        self.url = url
        self._body = body

    def read(self, limit: int = MAX_RESPONSE_BYTES + 1) -> bytes:
        return self._body[:limit]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _http_get(url: str) -> _Response:
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
    })
    try:
        with build_opener(_NoRedirect()).open(request, timeout=15) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            return _Response(response.status, response.geturl(), body)
    except HTTPError as error:
        return _Response(error.code, error.geturl(), error.read(MAX_RESPONSE_BYTES + 1))
    except (URLError, TimeoutError, OSError) as error:
        raise ProbeSkipped("network error while checking source") from error


def _robots_rules(url: str, get=_http_get) -> tuple[RobotFileParser | None, int, int]:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        response = get(robots_url)
    except ProbeSkipped as error:
        error.report.update({
            "robots_http_status": None,
            "robots_decision": "unavailable",
            "robots_path_allowed": None,
        })
        raise
    if response.status == 404:
        # A missing robots file publishes no path restrictions.
        return None, 0, response.status
    if response.status != 200:
        raise ProbeSkipped(
            f"robots.txt returned HTTP {response.status}",
            report={
                "robots_http_status": response.status,
                "robots_decision": "unavailable",
                "robots_path_allowed": None,
            },
        )
    if urlsplit(response.url).hostname != parts.hostname:
        raise ProbeSkipped(
            "robots.txt redirected to another host",
            report={
                "robots_http_status": response.status,
                "robots_decision": "unavailable",
                "robots_path_allowed": None,
            },
        )
    if len(response.read()) > MAX_RESPONSE_BYTES:
        raise ProbeSkipped(
            "robots.txt exceeded the response-size limit",
            report={
                "robots_http_status": response.status,
                "robots_decision": "unavailable",
                "robots_path_allowed": None,
            },
        )

    parser = RobotFileParser(robots_url)
    parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
    delay = parser.crawl_delay(USER_AGENT)
    if delay is None:
        delay = parser.crawl_delay("*")
    return parser, int(delay or 0), response.status


class _FactsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_titles: list[str] = []
        self.page_titles: list[str] = []
        self.text: list[str] = []
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"h1", "title"}:
            self._capture = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._capture == tag:
            value = " ".join(" ".join(self._buffer).split())
            if value and tag == "h1":
                self.h1_titles.append(value)
            elif value and tag == "title":
                self.page_titles.append(value)
            self._capture = None
            self._buffer = []

    def handle_data(self, data):
        if self._skip_depth:
            return
        clean = " ".join(data.split())
        if clean:
            self.text.append(clean)
            if self._capture:
                self._buffer.append(clean)


def _parse_italian_start(text: str) -> str | None:
    pattern = re.compile(
        r"\b(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})"
        r"(?:.{0,30}?\b(?:ore\s*)?(\d{1,2})[.:](\d{2}))?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    day, month_name, year, hour, minute = match.groups()
    month = MONTHS[month_name.casefold()]
    if hour is None:
        return date(int(year), month, int(day)).isoformat()
    local = datetime(int(year), month, int(day), int(hour), int(minute), tzinfo=ROME)
    return local.isoformat()


def _event_fields(html: str) -> dict:
    parser = _FactsParser()
    parser.feed(html)
    title = next(iter(parser.h1_titles), None) or next(iter(parser.page_titles), None)
    body_text = " ".join(parser.text)
    start_at = _parse_italian_start(body_text)
    venue_match = re.search(
        r"Giardini\s+Luzzati(?:\s*[-–]\s*(?:Spazio Comune|Area Archeologica))?",
        body_text,
        re.IGNORECASE,
    )
    venue = venue_match.group(0).strip() if venue_match else None
    return {
        "title": title,
        "start_at": start_at,
        "venue": venue,
    }


def probe_event(url: str = EVENT_URL, get=_http_get, sleeper=time.sleep) -> dict:
    parsed_url = urlsplit(url)
    fixed_url = urlsplit(EVENT_URL)
    if (parsed_url.scheme, parsed_url.hostname, parsed_url.path) != (
        fixed_url.scheme, fixed_url.hostname, fixed_url.path
    ):
        raise ProbeSkipped("URL is outside the fixed one-event probe")

    request_count = 0
    robots_http_status = None
    robots_decision = "not_checked"
    robots_path_allowed = None
    crawl_delay = 0
    event_http_status = None

    def tracked_get(target: str) -> _Response:
        nonlocal request_count
        request_count += 1
        return get(target)

    try:
        robots, crawl_delay, robots_http_status = _robots_rules(url, get=tracked_get)
        if robots is None:
            robots_decision = "missing_no_rules"
            robots_path_allowed = True
        else:
            robots_path_allowed = robots.can_fetch(USER_AGENT, url)
            robots_decision = "allowed" if robots_path_allowed else "disallowed"
            if not robots_path_allowed:
                raise ProbeSkipped("robots.txt disallows this event path")
        if crawl_delay > MAX_CRAWL_DELAY_SECONDS:
            raise ProbeSkipped("published crawl delay exceeds the probe's wait limit")
        if crawl_delay:
            sleeper(crawl_delay)

        response = tracked_get(url)
        event_http_status = response.status
        if response.status != 200:
            raise ProbeSkipped(f"event page returned HTTP {response.status}")
        if urlsplit(response.url).hostname != fixed_url.hostname:
            raise ProbeSkipped("event page redirected to another host")
        html_bytes = response.read()
        if len(html_bytes) > MAX_RESPONSE_BYTES:
            raise ProbeSkipped("event page exceeded the response-size limit")
        facts = _event_fields(html_bytes.decode("utf-8", errors="replace"))
        if not facts["title"]:
            raise ProbeSkipped("could not identify an event title")
        return {
            "status": "ok",
            "source": SOURCE_NAME,
            "title": facts["title"],
            "start_at": facts["start_at"],
            "venue": facts["venue"],
            "url": url,
            "access": {
                "robots_http_status": robots_http_status,
                "robots_decision": robots_decision,
                "robots_path_allowed": robots_path_allowed,
                "event_http_status": response.status,
                "request_count": request_count,
                "crawl_delay_seconds": crawl_delay,
            },
        }
    except ProbeSkipped as error:
        report = {
            "robots_http_status": robots_http_status,
            "robots_decision": robots_decision,
            "robots_path_allowed": robots_path_allowed,
            "event_http_status": event_http_status,
            "request_count": request_count,
            "crawl_delay_seconds": crawl_delay,
        }
        report.update(error.report)
        error.report = report
        raise


def main() -> int:
    try:
        result = probe_event()
    except ProbeSkipped as error:
        result = {
            "status": "skipped",
            "source": SOURCE_NAME,
            "reason": str(error),
            "url": EVENT_URL,
            **error.report,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
