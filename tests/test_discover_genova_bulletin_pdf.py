from pathlib import Path

from scripts.discover_genova_bulletin_pdf import discover_approved_page, discover_from_html


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "genova_bulletin_links"
PAGE_URL = "https://events.example.org/calendar/"
RETRIEVED = "2026-10-09T12:00:00+00:00"


def read_fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def discover(name, target="2026-10"):
    return discover_from_html(
        read_fixture(name), source_name="Example events", page_url=PAGE_URL,
        target_month=target, retrieved_at=RETRIEVED,
    )


def test_selects_current_month_pdf_and_preserves_selection_evidence():
    result = discover("matching.html")
    assert result["status"] == "found"
    assert result["pdf_url"] == "https://events.example.org/media/programma-ottobre-2026.pdf"
    assert result["detected_month"] == {"year": 2026, "month": 10, "label": "ottobre 2026"}
    assert result["discovery_evidence"]["link_text"] == "Scarica il programma di ottobre 2026"
    assert result["retrieval_timestamp"] == RETRIEVED
    assert discover("matching.html", target="2026-11")["status"] == "no_match"


def test_stale_missing_and_ambiguous_links_are_not_selected():
    stale = discover("stale.html")
    assert stale["status"] == "no_match"
    assert stale["pdf_url"] is None
    assert stale["pdf_links"][0]["matches_target"] is False

    ambiguous = discover("ambiguous.html")
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["pdf_url"] is None
    assert len(ambiguous["pdf_links"]) == 2

    missing = discover("no-pdf.html")
    assert missing["status"] == "no_match"
    assert missing["pdf_links"] == []


def test_offline_cli_outputs_candidate_json():
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "discover_genova_bulletin_pdf.py"),
         "--fixture-html", str(FIXTURES / "matching.html"), "--source-name", "Example events",
         "--page-url", PAGE_URL, "--month", "2026-10"],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout)["status"] == "found"


def test_inactive_source_never_makes_a_request():
    calls = []
    result = discover_approved_page(
        {"id": 12, "city": "genova", "name": "Candidate", "url": PAGE_URL, "status": "pending"},
        target_month="2026-10", get=lambda url: calls.append(url),
    )
    assert result["status"] == "blocked_source_not_active"
    assert result["request_count"] == 0
    assert calls == []


def test_active_discovery_checks_robots_and_fetches_only_the_page():
    calls = []

    class Response:
        def __init__(self, status, url, body=b""):
            self.status, self.url, self.body = status, url, body

        def read(self, limit=2_000_001):
            return self.body[:limit]

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return Response(404, url)
        return Response(200, url, read_fixture("matching.html").encode())

    result = discover_approved_page(
        {"id": 12, "city": "genova", "name": "Approved example", "url": PAGE_URL, "status": "active"},
        target_month="2026-10", get=get,
    )
    assert result["status"] == "found"
    assert result["request_count"] == 2
    assert result["pdf_downloaded"] is False
    assert calls == ["https://events.example.org/robots.txt", PAGE_URL]


def test_robots_disallow_prevents_page_and_pdf_requests():
    calls = []

    class Response:
        status = 200
        def __init__(self, url):
            self.url = url
        def read(self, limit=2_000_001):
            return b"User-agent: *\nDisallow: /calendar/\n"

    result = discover_approved_page(
        {"id": 12, "city": "genova", "name": "Approved example", "url": PAGE_URL, "status": "active"},
        target_month="2026-10", get=lambda url: calls.append(url) or Response(url),
    )
    assert result["status"] == "blocked_by_robots"
    assert result["request_count"] == 1
    assert calls == ["https://events.example.org/robots.txt"]
