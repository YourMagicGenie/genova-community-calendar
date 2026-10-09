#!/usr/bin/env python3
"""Find a current monthly PDF link on an approved Genova source page."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.probe_giardini_luzzati import (  # shared bounded HTTP/robots behavior
    MAX_CRAWL_DELAY_SECONDS,
    MAX_RESPONSE_BYTES,
    USER_AGENT,
    ProbeSkipped,
    _http_get,
    _robots_rules,
)


MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
    "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9,
    "ottobre": 10, "novembre": 11, "dicembre": 12,
}
MONTH_PATTERN = "|".join(MONTHS)
MONTH_YEAR_RE = re.compile(rf"(?i)\b({MONTH_PATTERN})\s+(20\d{{2}})\b")
MONTH_RE = re.compile(rf"(?i)\b({MONTH_PATTERN})\b")
MAX_PAGE_BYTES = 512_000
MAX_REQUESTS = 2  # robots.txt plus the configured page; never fetch the PDF here.


class _LinksAndText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.visible = []
        self._anchor = None
        self._anchor_text = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            self._anchor = attrs
            self._anchor_text = []

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "a" and self._anchor is not None:
            self.links.append({
                "href": self._anchor.get("href"),
                "text": " ".join(" ".join(self._anchor_text).split()),
                "type": self._anchor.get("type", ""),
                "title": self._anchor.get("title", ""),
            })
            self._anchor = None
            self._anchor_text = []

    def handle_data(self, data):
        if self._skip_depth:
            return
        clean = " ".join(data.split())
        if clean:
            self.visible.append(clean)
            if self._anchor is not None:
                self._anchor_text.append(clean)


def _month_context(text: str) -> list[dict]:
    contexts = {}
    for match in MONTH_YEAR_RE.finditer(text):
        key = (int(match.group(2)), MONTHS[match.group(1).casefold()])
        contexts[key] = {"year": key[0], "month": key[1], "label": match.group(0)}
    return list(contexts.values())


def _link_months(text: str) -> list[dict]:
    clues = {}
    for match in MONTH_YEAR_RE.finditer(text):
        key = (int(match.group(2)), MONTHS[match.group(1).casefold()])
        clues[key] = {"year": key[0], "month": key[1], "label": match.group(0)}
    for match in MONTH_RE.finditer(text):
        month = MONTHS[match.group(1).casefold()]
        if not any(item["month"] == month for item in clues.values()):
            clues[(None, month)] = {"year": None, "month": month, "label": match.group(0)}
    return list(clues.values())


def _target(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(20\d{2})-(0[1-9]|1[0-2])", value)
    if not match:
        raise ValueError("target month must use YYYY-MM")
    return int(match.group(1)), int(match.group(2))


def discover_from_html(
    html: str,
    *,
    source_name: str,
    page_url: str,
    target_month: str,
    retrieved_at: str | None = None,
) -> dict:
    """Select a monthly PDF link from supplied page HTML without network I/O."""
    target_year, target_number = _target(target_month)
    parser = _LinksAndText()
    parser.feed(html)
    page_contexts = _month_context(" ".join(parser.visible))
    links = []
    seen = set()
    for link in parser.links:
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        pdf_url = urljoin(page_url, href.strip())
        parsed = urlsplit(pdf_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if not (parsed.path.casefold().endswith(".pdf") or "application/pdf" in link["type"].casefold()):
            continue
        pdf_url = parsed._replace(fragment="").geturl()
        if pdf_url in seen:
            continue
        seen.add(pdf_url)
        signals = " ".join((link["text"], link["title"], parsed.path))
        clues = _link_months(signals)
        if not clues and len(page_contexts) == 1:
            clues = page_contexts
        elif len(clues) == 1 and clues[0]["year"] is None and len(page_contexts) == 1:
            context = page_contexts[0]
            if context["month"] == clues[0]["month"]:
                clues = [{**clues[0], "year": context["year"], "context": context["label"]}]
        match = len(clues) == 1 and clues[0]["year"] == target_year and clues[0]["month"] == target_number
        uncertain_current = len(clues) == 1 and clues[0]["year"] is None and clues[0]["month"] == target_number
        links.append({
            "pdf_url": pdf_url,
            "detected_month": clues[0] if len(clues) == 1 else None,
            "matches_target": match,
            "year_uncertain_current_month": uncertain_current,
            "evidence": {
                "link_text": link["text"] or None,
                "link_title": link["title"] or None,
                "url_path": parsed.path,
                "month_context": clues[0].get("context") if len(clues) == 1 else None,
            },
        })

    matches = [link for link in links if link["matches_target"]]
    uncertain = [link for link in links if link["year_uncertain_current_month"]]
    if len(matches) == 1 and not uncertain:
        status, selected = "found", matches[0]
    elif matches or uncertain:
        status, selected = "ambiguous", None
    else:
        status, selected = "no_match", None
    stamp = retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "status": status,
        "source_name": source_name,
        "page_url": page_url,
        "pdf_url": selected["pdf_url"] if selected else None,
        "detected_month": selected["detected_month"] if selected else None,
        "discovery_evidence": selected["evidence"] if selected else None,
        "retrieval_timestamp": stamp,
        "target_month": target_month,
        "pdf_links": links,
    }


def discover_approved_page(source: dict, *, target_month: str, get=_http_get) -> dict:
    """Discover from an already-active source; never download the linked PDF."""
    if (not isinstance(source, dict) or source.get("status") != "active"
            or source.get("city") != "genova" or not isinstance(source.get("id"), int)):
        return {"status": "blocked_source_not_active", "request_count": 0, "pdf_url": None}
    page_url = source.get("url")
    parsed = urlsplit(page_url or "")
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return {"status": "blocked_invalid_source_url", "request_count": 0, "pdf_url": None}
    calls = 0

    def tracked_get(url):
        nonlocal calls
        calls += 1
        if calls > MAX_REQUESTS:
            raise ProbeSkipped("monthly PDF discovery request budget exceeded")
        return get(url)

    try:
        robots, crawl_delay, robots_status = _robots_rules(page_url, get=tracked_get)
        if robots is not None and not robots.can_fetch(USER_AGENT, page_url):
            return {"status": "blocked_by_robots", "request_count": calls, "robots_http_status": robots_status, "pdf_url": None}
        if crawl_delay > MAX_CRAWL_DELAY_SECONDS:
            return {"status": "blocked_crawl_delay", "request_count": calls, "robots_http_status": robots_status, "pdf_url": None}
        if crawl_delay:
            time.sleep(crawl_delay)
        response = tracked_get(page_url)
        page_status = response.status
        if page_status != 200 or urlsplit(response.url).hostname != parsed.hostname:
            return {"status": "page_unavailable", "request_count": calls, "robots_http_status": robots_status, "page_http_status": page_status, "pdf_url": None}
        page_bytes = response.read(MAX_PAGE_BYTES + 1)
        if len(page_bytes) > MAX_PAGE_BYTES or len(page_bytes) > MAX_RESPONSE_BYTES:
            return {"status": "page_too_large", "request_count": calls, "pdf_url": None}
        result = discover_from_html(
            page_bytes.decode("utf-8", errors="replace"), source_name=source.get("name", "Genova source"), page_url=page_url,
            target_month=target_month,
        )
        result.update({
            "request_count": calls,
            "robots_http_status": robots_status,
            "robots_decision": "missing_no_rules" if robots is None else "allowed",
            "crawl_delay_seconds": crawl_delay,
            "page_http_status": page_status,
            "pdf_downloaded": False,
        })
        return result
    except ProbeSkipped as exc:
        return {"status": "skipped", "reason": str(exc), "request_count": calls, "pdf_url": None}
    except Exception as exc:
        return {"status": "access_error", "error_type": type(exc).__name__, "request_count": calls, "pdf_url": None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-html", type=Path, required=True, help="offline page HTML fixture")
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--page-url", required=True)
    parser.add_argument("--month", required=True, help="target month in YYYY-MM form")
    args = parser.parse_args(argv)
    result = discover_from_html(
        args.fixture_html.read_text(encoding="utf-8"), source_name=args.source_name,
        page_url=args.page_url, target_month=args.month,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("status") in {"found", "no_match", "ambiguous"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
