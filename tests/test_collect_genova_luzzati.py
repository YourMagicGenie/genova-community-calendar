from pathlib import Path

import pytest

from scripts.collect_genova_luzzati import INDEX_URL, ProbeSkipped, collect, parse_index


FIXTURE = Path(__file__).parent / "fixtures" / "genova" / "luzzati-index.html"


class FakeResponse:
    def __init__(self, status, url, body=b""):
        self.status = status
        self.url = url
        self.body = body

    def read(self, limit=2_000_001):
        return self.body[:limit]


def active_source(_url=INDEX_URL):
    return {
        "id": 51,
        "city": "genova",
        "url": INDEX_URL,
        "name": "Giardini Luzzati / Spazio Comune",
        "status": "active",
        "feed_type": "web_index",
        "publisher_url": "https://www.spazio-comune.org/",
        "discovery_method": "manual",
    }


def test_index_parser_preserves_unknowns_and_separate_showtimes():
    events = parse_index(FIXTURE.read_text(encoding="utf-8"), 51)

    assert len(events) == 4
    known = next(event for event in events if event["title"] == "Nessuno ci insegna a cadere")
    assert known["start_time"] == "2026-10-06T18:00:00+02:00"
    assert known["location"] == "Giardini Luzzati - Spazio Comune"
    assert known["description"] if "description" in known else True
    assert known["review_status"] == "needs_review"

    unknown = next(event for event in events if event["title"] == "Evento senza data")
    assert unknown["start_time"] is None
    assert unknown["location"] is None

    showtimes = [event for event in events if event["title"] == "Doppio turno"]
    assert [event["start_time"] for event in showtimes] == [
        "2026-10-07T19:00:00+02:00",
        "2026-10-07T21:30:00+02:00",
    ]
    assert len({event["source_uid"] for event in showtimes}) == 2


def test_index_parser_deduplicates_repeated_product_links():
    html = """
    <ul><li class="product">
      <a href="/prodotto/a/"><span>image</span></a>
      <a href="/prodotto/a/"><h2>A</h2></a>
      <p>6 ottobre 2026 ore 18.00</p>
    </li></ul>
    """
    events = parse_index(html, 51)
    assert len(events) == 1
    assert events[0]["title"] == "A"


def test_collection_checks_active_source_then_robots_then_one_index_get():
    calls = []
    body = FIXTURE.read_bytes()

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, url, b"User-agent: *\nAllow: /categoria-prodotto/eventi/\n")
        return FakeResponse(200, url, body)

    result = collect(source_loader=active_source, get=get, sleeper=lambda _: None)

    assert calls == ["https://www.spazio-comune.org/robots.txt", INDEX_URL]
    assert result["access"]["request_count"] == 2
    assert result["access"]["robots_decision"] == "allowed"
    assert result["events_found"] == 4
    assert all(set(event) <= {
        "feed_id", "title", "start_time", "end_time", "location", "publisher", "url",
        "normalized_url", "source_uid", "category", "category_confidence", "review_status"
    } for event in result["events"])


def test_collection_fails_closed_before_web_fetch_when_source_is_not_active():
    calls = []

    def unavailable(_url):
        raise ProbeSkipped("exactly one active Giardini Luzzati source is required")

    with pytest.raises(ProbeSkipped, match="active"):
        collect(source_loader=unavailable, get=lambda url: calls.append(url))

    assert calls == []


def test_collection_stops_when_exact_index_path_is_disallowed():
    calls = []

    def get(url):
        calls.append(url)
        return FakeResponse(200, url, b"User-agent: *\nDisallow: /categoria-prodotto/eventi/\n")

    with pytest.raises(ProbeSkipped, match="disallows"):
        collect(source_loader=active_source, get=get, sleeper=lambda _: None)

    assert calls == ["https://www.spazio-comune.org/robots.txt"]
