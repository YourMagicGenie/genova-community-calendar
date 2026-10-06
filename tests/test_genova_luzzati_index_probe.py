from __future__ import annotations

from scripts.probe_giardini_luzzati_index import INDEX_URL, ProbeSkipped, probe_index


INDEX_PAGE = """<!doctype html>
<html>
<head><title>Eventi - Spazio Comune</title></head>
<body>
<h1>Eventi</h1>
<p>Page copy must not be returned by the probe.</p>
<a href="/prodotto/example/">Example event</a>
</body>
</html>"""


class FakeResponse:
    def __init__(self, status, url, body=b""):
        self.status = status
        self.url = url
        self.body = body

    def read(self, limit=2_000_001):
        return self.body[:limit]


def test_index_probe_checks_robots_then_one_index_page():
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(
                200,
                url,
                b"User-agent: *\nAllow: /categoria-prodotto/eventi/\n",
            )
        return FakeResponse(200, url, INDEX_PAGE.encode("utf-8"))

    result = probe_index(get=get, sleeper=lambda _: None)

    assert calls == [
        "https://www.spazio-comune.org/robots.txt",
        INDEX_URL,
    ]
    assert result["status"] == "ok"
    assert result["recognized_event_index"] is True
    assert result["heading"] == "Eventi"
    assert result["page_title"] == "Eventi - Spazio Comune"
    assert result["access"] == {
        "robots_http_status": 200,
        "robots_decision": "allowed",
        "robots_path_allowed": True,
        "page_http_status": 200,
        "request_count": 2,
        "crawl_delay_seconds": 0,
    }
    assert "Page copy" not in str(result)
    assert "Example event" not in str(result)


def test_index_probe_disallow_stops_before_index_request():
    calls = []

    def get(url):
        calls.append(url)
        return FakeResponse(
            200,
            url,
            b"User-agent: *\nDisallow: /categoria-prodotto/eventi/\n",
        )

    try:
        probe_index(get=get, sleeper=lambda _: None)
    except ProbeSkipped as error:
        assert "disallows" in str(error)
        assert error.report["robots_decision"] == "disallowed"
        assert error.report["robots_path_allowed"] is False
        assert error.report["page_http_status"] is None
        assert error.report["request_count"] == 1
    else:
        raise AssertionError("disallowed index path must be skipped")

    assert calls == ["https://www.spazio-comune.org/robots.txt"]


def test_index_probe_reports_missing_candidate_route():
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(404, url)
        return FakeResponse(404, url)

    try:
        probe_index(get=get, sleeper=lambda _: None)
    except ProbeSkipped as error:
        assert "HTTP 404" in str(error)
        assert error.report["robots_http_status"] == 404
        assert error.report["robots_decision"] == "missing_no_rules"
        assert error.report["robots_path_allowed"] is True
        assert error.report["page_http_status"] == 404
        assert error.report["request_count"] == 2
    else:
        raise AssertionError("missing candidate route must be reported as skipped")
