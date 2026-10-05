from __future__ import annotations

from scripts.probe_giardini_luzzati import EVENT_URL, USER_AGENT, ProbeSkipped, probe_event


PAGE = """<!doctype html>
<html><head><title>Spazio Comune</title></head><body>
<h1>Nessuno ci insegna a cadere</h1>
<h2>Martedì 6 ottobre 2026 – ore 18.00 Giardini Luzzati - Spazio Comune</h2>
<p>This long promotional description must not be returned or saved.</p>
<img src="cover-image.jpg" alt="cover">
</body></html>"""


class FakeResponse:
    def __init__(self, status, url, body=b""):
        self.status = status
        self.url = url
        self.body = body

    def read(self, limit=2_000_001):
        return self.body[:limit]


def test_robots_disallow_skips_event_without_fetching_page():
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, url, b"User-agent: *\nDisallow: /prodotto/\n")
        raise AssertionError("event page must not be fetched")

    try:
        probe_event(get=get, sleeper=lambda _: None)
    except ProbeSkipped as error:
        assert "disallows" in str(error)
    else:
        raise AssertionError("disallowed path must be skipped")

    assert calls == ["https://www.spazio-comune.org/robots.txt"]


def test_robots_404_allows_one_page_and_returns_only_calendar_facts():
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(404, url)
        return FakeResponse(200, url, PAGE.encode("utf-8"))

    result = probe_event(get=get, sleeper=lambda _: None)

    assert calls == [
        "https://www.spazio-comune.org/robots.txt",
        EVENT_URL,
    ]
    assert result == {
        "status": "ok",
        "source": "Giardini Luzzati / Spazio Comune",
        "title": "Nessuno ci insegna a cadere",
        "start_at": "2026-10-06T18:00:00+02:00",
        "venue": "Giardini Luzzati - Spazio Comune",
        "url": EVENT_URL,
    }
    assert "description" not in result
    assert "image" not in result
    assert "promotional" not in str(result)


def test_robots_network_error_stops_before_event_request():
    calls = []

    def get(url):
        calls.append(url)
        return FakeResponse(503, url)

    try:
        probe_event(get=get, sleeper=lambda _: None)
    except ProbeSkipped as error:
        assert "HTTP 503" in str(error)
    else:
        raise AssertionError("unavailable robots file must fail closed")

    assert calls == ["https://www.spazio-comune.org/robots.txt"]


def test_source_probe_uses_identifying_user_agent():
    assert "GenovaCommunityCalendarProbe" in USER_AGENT
