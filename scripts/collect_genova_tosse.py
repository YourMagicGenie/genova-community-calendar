#!/usr/bin/env python3
"""Manual, bounded, facts-only Tosse comparison. No database writes or activation."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.probe_giardini_luzzati import (ProbeSkipped, _http_get, _robots_rules,
    MAX_RESPONSE_BYTES, MAX_CRAWL_DELAY_SECONDS, USER_AGENT)

INDEX_URL = 'https://teatrodellatosse.it/eventi/'
HOST = 'teatrodellatosse.it'
ROME = ZoneInfo('Europe/Rome')
MAX_DETAILS = 3
SAMPLE_URLS = tuple(INDEX_URL + slug + '.htm' for slug in (
    'il-bancone-confessionale', 'genova-music-day', 'a-cena-con-macbeth'))
DATE = re.compile(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b')
CLOCK = re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\b')
VENUES = ('Luzzati Lab', 'La Claque', 'Sala Aldo Trionfo', 'Sala Dino Campana',
          'Sala Agorà', 'Teatro del Ponente')


def detail_url(url):
    p = urlsplit(url)
    return (p.scheme == 'https' and p.netloc == HOST and not p.query and not p.fragment
            and bool(re.fullmatch(r'/eventi/[a-zA-Z0-9_-]+\.htm', p.path)))


class Page(HTMLParser):
    """Transient visible tokens and table rows; never serialize source content."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = []
        self.title = []
        self.in_title = False
        self.title_buffer = []
        self.links = []
        self.tokens = []
        self.rows = []
        self.row = None
        self.row_scope = False
        self.schedule = False
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'svg'}:
            self.skip.append(tag)
        if self.skip:
            return
        attrs = dict(attrs)
        if tag == 'h1':
            self.in_title = True
            self.title_buffer = []
        if tag == 'a' and attrs.get('href'):
            url = urljoin(INDEX_URL, attrs['href'])
            if detail_url(url):
                self.links.append(url)
        if tag == 'tr':
            self.row = []
            self.row_scope = self.schedule
    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag == 'h1':
            self.in_title = False
            if self.title_buffer:
                self.title.append(' '.join(self.title_buffer))
        if tag == 'tr' and self.row is not None:
            if self.row_scope:
                self.rows.append(' '.join(self.row))
            self.row = None
    def handle_data(self, data):
        if self.skip:
            return
        value = ' '.join(data.split())
        if not value:
            return
        if self.in_title:
            self.title_buffer.append(value)
        if value.casefold() == 'programmazione':
            self.schedule = True
        elif value.casefold() in {'altri spettacoli', 'spettacoli correlati'}:
            self.schedule = False
        if self.schedule:
            self.tokens.append(value)
        if self.row is not None:
            self.row.append(value)


def local_start(match, clock):
    day, month, year = map(int, match.groups())
    hour, minute = map(int, clock.groups())
    try:
        naive = datetime(year, month, day, hour, minute)
        candidates = {aware.utcoffset(): aware for fold in (0, 1)
                      if (aware := naive.replace(tzinfo=ROME, fold=fold)).astimezone(timezone.utc)
                      .astimezone(ROME).replace(tzinfo=None) == naive}
        # Reject nonexistent and ambiguous local times instead of choosing a fold.
        return next(iter(candidates.values())).isoformat() if len(candidates) == 1 else None
    except ValueError:
        return None


def parse_index(html):
    page = Page()
    page.feed(html)
    return list(dict.fromkeys(page.links))


def parse_detail(html, url):
    if not detail_url(url):
        raise ProbeSkipped('detail URL outside Tosse allowlist')
    page = Page()
    page.feed(html)
    title = next(iter(page.title), None)
    # Table rows are authoritative. A token fallback handles responsive layouts
    # by pairing only the interval between consecutive full calendar dates.
    rows = page.rows
    method = 'programmazione_table'
    if not rows:
        text = ' '.join(page.tokens)
        dates = list(DATE.finditer(text))
        rows = [text[m.start():dates[i+1].start() if i+1 < len(dates) else len(text)]
                for i, m in enumerate(dates)]
        method = 'programmazione_date_segment'
    events, reasons, seen = [], set(), set()
    for row in rows:
        dates, clocks = list(DATE.finditer(row)), list(CLOCK.finditer(row))
        venue = next((v for v in VENUES if re.search(re.escape(v), row, re.I)), None)
        if len(dates) != 1 or len(clocks) != 1:
            if dates or clocks:
                reasons.add('schedule_row_date_time_unresolved')
            continue
        start = local_start(dates[0], clocks[0])
        if not start:
            reasons.add('invalid_or_ambiguous_local_time')
            continue
        if start in seen:
            continue
        seen.add(start)
        category = None
        # Publisher section labels are conservative hints, not a venue default.
        # Event-page title alone may establish music; otherwise retain unknown.
        if title and re.search(r'\b(music|musica|concerto|jazz)\b', title, re.I):
            category = 'music'
        events.append(dict(title=title, start_time=start, end_time=None, location=venue,
            publisher='Teatro della Tosse', url=url, normalized_url=url,
            source_uid='genova-tosse:' + hashlib.sha256(f'{url}|{start}'.encode()).hexdigest(),
            category=category, category_confidence=0.82 if category else None,
            review_status='needs_review', evidence_note=f'date_time={method}; timezone=Europe/Rome'))
    if not events:
        reasons.add('no_explicit_schedule_occurrence')
    if not title:
        reasons.add('title_missing')
    if any(not e['location'] for e in events):
        reasons.add('location_missing_or_unsupported')
    if not events or any(not e['category'] for e in events):
        reasons.add('category_unsupported')
    return dict(url=url, events=events, unresolved_reasons=sorted(reasons),
                date_time_method=method, schedule_rows_checked=len(rows))


def collect(*, get=_http_get, sleeper=time.sleep, detail_limit=2, sample_only=False):
    if isinstance(detail_limit, bool) or not isinstance(detail_limit, int) or not 1 <= detail_limit <= MAX_DETAILS:
        raise ProbeSkipped('detail limit must be 1–3')
    count = 0
    def tracked(url):
        nonlocal count
        count += 1
        return get(url)
    robots, delay, status = _robots_rules(INDEX_URL, get=tracked)
    if delay > MAX_CRAWL_DELAY_SECONDS:
        raise ProbeSkipped('published crawl delay exceeds wait limit')
    def read(url):
        if robots and not robots.can_fetch(USER_AGENT, url):
            raise ProbeSkipped('robots.txt disallows requested path')
        sleeper(max(delay, 1))
        response = tracked(url)
        if response.status != 200:
            raise ProbeSkipped(f'Tosse returned HTTP {response.status}; stopping without retry')
        if response.url != url:
            raise ProbeSkipped('unexpected redirect; stopping without following')
        body = response.read()
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProbeSkipped('response size limit exceeded')
        return body.decode('utf-8', errors='replace')
    candidates = list(SAMPLE_URLS) if sample_only else parse_index(read(INDEX_URL))
    results = []
    for url in candidates[:detail_limit]:
        results.append(parse_detail(read(url), url))
    events = [e for result in results for e in result['events']]
    return dict(status='ok', mode='known_detail_comparison' if sample_only else 'index_comparison',
        source_url=INDEX_URL, activation='unchanged', persistence='none',
        access=dict(request_count=count, robots_http_status=status,
                    detail_page_limit=detail_limit, detail_pages_checked=len(results),
                    crawl_delay_seconds=delay),
        candidate_urls=len(candidates), candidates=results, events=events, events_found=len(events))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--detail-limit', type=int, default=2)
    parser.add_argument('--sample-only', action='store_true', help='known detail URLs; no index request')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        report = collect(detail_limit=args.detail_limit, sample_only=args.sample_only)
        code = 0
    except ProbeSkipped as error:
        report = dict(status='skipped', reason=str(error), persistence='none')
        code = 2
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'events_found', 'access', 'reason') if k in report}))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
