#!/usr/bin/env python3
"""Bounded read-only probe for the candidate Giardini Luzzati event index.

Checks robots.txt for the exact candidate path, then makes at most one request
to that fixed index URL when permitted. Prints only access metadata and the
page title/heading needed to decide whether the route is an event index.
"""
from __future__ import annotations

import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

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


class _IndexIdentityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page_title: str | None = None
        self.heading: str | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"title", "h1"} and self._capture is None:
            self._capture = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._capture == tag:
            value = " ".join(" ".join(self._buffer).split())
            if value:
                if tag == "title" and self.page_title is None:
                    self.page_title = value
                elif tag == "h1" and self.heading is None:
                    self.heading = value
            self._capture = None
            self._buffer = []

    def handle_data(self, data):
        if self._skip_depth or self._capture is None:
            return
        clean = " ".join(data.split())
        if clean:
            self._buffer.append(clean)


def _identify_index(html: str) -> dict:
    parser = _IndexIdentityParser()
    parser.feed(html)
    labels = [value for value in (parser.heading, parser.page_title) if value]
    recognized = any(re.search(r"\beventi\b", value, re.IGNORECASE) for value in labels)
    return {
        "page_title": parser.page_title,
        "heading": parser.heading,
        "recognized_event_index": recognized,
    }


def probe_index(url: str = INDEX_URL, get=_http_get, sleeper=time.sleep) -> dict:
    parsed_url = urlsplit(url)
    fixed_url = urlsplit(INDEX_URL)
    if (parsed_url.scheme, parsed_url.hostname, parsed_url.path) != (
        fixed_url.scheme,
        fixed_url.hostname,
        fixed_url.path,
    ):
        raise ProbeSkipped("URL is outside the fixed event-index probe")

    request_count = 0
    robots_http_status = None
    robots_decision = "not_checked"
    robots_path_allowed = None
    crawl_delay = 0
    page_http_status = None

    def tracked_get(target: str):
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
                raise ProbeSkipped("robots.txt disallows this event-index path")

        if crawl_delay > MAX_CRAWL_DELAY_SECONDS:
            raise ProbeSkipped("published crawl delay exceeds the probe's wait limit")
        if crawl_delay:
            sleeper(crawl_delay)

        response = tracked_get(url)
        page_http_status = response.status
        if response.status != 200:
            raise ProbeSkipped(f"event-index page returned HTTP {response.status}")
        if urlsplit(response.url).hostname != fixed_url.hostname:
            raise ProbeSkipped("event-index page redirected to another host")

        html_bytes = response.read()
        if len(html_bytes) > MAX_RESPONSE_BYTES:
            raise ProbeSkipped("event-index page exceeded the response-size limit")

        identity = _identify_index(html_bytes.decode("utf-8", errors="replace"))
        return {
            "status": "ok",
            "source": SOURCE_NAME,
            "url": url,
            **identity,
            "access": {
                "robots_http_status": robots_http_status,
                "robots_decision": robots_decision,
                "robots_path_allowed": robots_path_allowed,
                "page_http_status": page_http_status,
                "request_count": request_count,
                "crawl_delay_seconds": crawl_delay,
            },
        }
    except ProbeSkipped as error:
        report = {
            "robots_http_status": robots_http_status,
            "robots_decision": robots_decision,
            "robots_path_allowed": robots_path_allowed,
            "page_http_status": page_http_status,
            "request_count": request_count,
            "crawl_delay_seconds": crawl_delay,
        }
        report.update(error.report)
        error.report = report
        raise


def main() -> int:
    try:
        result = probe_index()
    except ProbeSkipped as error:
        result = {
            "status": "skipped",
            "source": SOURCE_NAME,
            "reason": str(error),
            "url": INDEX_URL,
            **error.report,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
