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
    assert "description" not in known
    assert "image_url" not in known
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

    result = collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=0)

    assert calls == ["https://www.spazio-comune.org/robots.txt", INDEX_URL]
    assert result["access"]["request_count"] == 2
    assert result["access"]["robots_decision"] == "allowed"
    assert result["events_found"] == 4
    assert result["diagnostics"]["distinct_candidate_urls"] == 3
    assert result["diagnostics"]["records_with_titles"] == 3
    assert all(set(event) <= {
        "feed_id", "title", "start_time", "end_time", "location", "publisher", "url",
        "normalized_url", "source_uid", "category", "category_confidence", "review_status", "evidence_note",
        "is_all_day"
    } for event in result["events"])


def test_collection_fails_closed_before_web_fetch_when_source_is_not_active():
    calls = []
    source = active_source()
    source["status"] = "paused"

    with pytest.raises(ProbeSkipped, match="approval state"):
        collect(source, get=lambda url: calls.append(url))

    assert calls == []


def test_collection_stops_when_exact_index_path_is_disallowed():
    calls = []

    def get(url):
        calls.append(url)
        return FakeResponse(200, url, b"User-agent: *\nDisallow: /categoria-prodotto/eventi/\n")

    with pytest.raises(ProbeSkipped, match="disallows"):
        collect(active_source(), get=get, sleeper=lambda _: None)

    assert calls == ["https://www.spazio-comune.org/robots.txt"]


def test_index_parser_handles_div_and_article_theme_cards_with_safe_diagnostics():
    html = FIXTURE.parent.joinpath("luzzati-index-div-cards.html").read_text(encoding="utf-8")
    diagnostics = {}

    events = parse_index(html, 51, diagnostics=diagnostics)

    assert [event["title"] for event in events] == ["Concerto di prova", "Laboratorio aperto"]
    assert events[0]["start_time"] == "2026-10-09T20:30:00+02:00"
    assert events[0]["location"] == "Giardini Luzzati - Spazio Comune"
    assert events[1]["start_time"] is None
    assert diagnostics == {
        "same_host_product_links": 3,
        "distinct_candidate_urls": 2,
        "candidate_records": 2,
        "records_with_titles": 2,
        "records_with_dates": 1,
        "records_with_times": 1,
    }
    assert all("description" not in event and "image" not in event for event in events)


def test_index_parser_reports_empty_index_without_retaining_page_content():
    html = FIXTURE.parent.joinpath("luzzati-index-empty.html").read_text(encoding="utf-8")
    diagnostics = {}

    events = parse_index(html, 51, diagnostics=diagnostics)

    assert events == []
    assert diagnostics == {
        "same_host_product_links": 0,
        "distinct_candidate_urls": 0,
        "candidate_records": 0,
        "records_with_titles": 0,
        "records_with_dates": 0,
        "records_with_times": 0,
    }


def test_index_parser_diagnostics_expose_candidates_missing_a_title():
    html = FIXTURE.parent.joinpath("luzzati-index-untitled.html").read_text(encoding="utf-8")
    diagnostics = {}

    events = parse_index(html, 51, diagnostics=diagnostics)

    assert events == []
    assert diagnostics == {
        "same_host_product_links": 1,
        "distinct_candidate_urls": 1,
        "candidate_records": 1,
        "records_with_titles": 0,
        "records_with_dates": 1,
        "records_with_times": 1,
    }


def _detail_index_event():
    return {
        "feed_id": 51,
        "title": "Titolo dall'indice",
        "start_time": None,
        "end_time": None,
        "location": None,
        "publisher": "Giardini Luzzati",
        "url": "https://www.spazio-comune.org/prodotto/prova/",
        "normalized_url": "https://www.spazio-comune.org/prodotto/prova/",
    }


def test_detail_text_extracts_showtimes_venue_and_explicit_category():
    from scripts.collect_genova_luzzati import parse_detail

    html = (FIXTURE.parent / "luzzati-detail-text.html").read_text(encoding="utf-8")
    events = parse_detail(html, _detail_index_event(), 51)
    assert [event["start_time"] for event in events] == [
        "2026-10-06T18:00:00+02:00", "2026-10-06T20:30:00+02:00"
    ]
    assert all(event["location"] == "Giardini Luzzati - Spazio Comune" for event in events)
    assert all(event["category"] == "music" and event["category_confidence"] == 0.85 for event in events)
    assert all(event["review_status"] == "needs_review" for event in events)



def test_detail_falls_back_to_full_page_when_event_facts_are_outside_summary_and_infers_category():
    from scripts.collect_genova_luzzati import parse_detail

    html = """
    <html><head><meta name="description" content="Un concerto jazz dal vivo per la serata."></head>
    <body><main class="product-summary"><h1>Concerto jazz al tramonto</h1><p>Una serata musicale.</p></main>
    <div class="event-date">Martedì 6 ottobre 2026 – ore 18.00</div>
    <p>Giardini Luzzati - Spazio Comune</p></body></html>
    """
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["title"] == "Concerto jazz al tramonto"
    assert event["start_time"] == "2026-10-06T18:00:00+02:00"
    assert event["location"] == "Giardini Luzzati - Spazio Comune"
    assert event["category"] == "music"
    assert event["category_confidence"] == 0.82
    assert "date_time=visible_event_text" in event["evidence_note"]


@pytest.mark.parametrize(
    ("title", "description", "expected", "confidence"),
    [
        ("Laboratorio di ceramica", "Attività pratica aperta a tutti.", "talks-workshops", 0.82),
        ("Una serata speciale", "Proiezione cinematografica in lingua originale.", "art-exhibitions", 0.76),
        ("Escursione urbana", "Passeggiata guidata nel centro storico.", "outdoors-tours", 0.82),
        ("Jazzercise", "Una serata nel quartiere.", None, None),
    ],
)
def test_detail_category_is_inferred_from_title_and_source_description(title, description, expected, confidence):
    from scripts.collect_genova_luzzati import parse_detail

    html = f"<html><body><main><h1>{title}</h1><p>{description}</p></main></body></html>"
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["category"] == expected
    assert event["category_confidence"] == confidence



def test_detail_category_uses_event_description_and_ignores_sitewide_footer():
    from scripts.collect_genova_luzzati import parse_detail

    html = """
    <html><body>
      <main class="product-summary">
        <h1>Eravamo comunisti - Massimo D’Alema</h1>
        <p>Presentazione del libro con l’autore e dibattito pubblico.</p>
      </main>
      <footer><p>Spazio Comune: luogo di incontro, comunità e socialità.</p></footer>
    </body></html>
    """
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["category"] == "talks-workshops"
    assert event["category_confidence"] == 0.76
    assert "category=title_or_description_keywords" in event["evidence_note"]


def test_detail_documentary_screening_is_not_misclassified_by_discussion_language():
    from scripts.collect_genova_luzzati import parse_detail

    html = """
    <html><body>
      <main class="product-summary">
        <h1>Ballata Femmenella</h1>
        <p>Proiezione del documentario e del film, con incontro e confronto con il pubblico.</p>
      </main>
      <footer><p>Comunità, socialità, eventi e incontri ai Giardini Luzzati.</p></footer>
    </body></html>
    """
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["category"] == "art-exhibitions"
    assert event["category_confidence"] == 0.76


def test_detail_structured_metadata_is_timezone_normalized():
    from scripts.collect_genova_luzzati import parse_detail

    html = (FIXTURE.parent / "luzzati-detail-structured.html").read_text(encoding="utf-8")
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["start_time"] == "2026-10-12T20:30:00+02:00"
    assert event["end_time"] == "2026-10-12T22:00:00+02:00"
    assert event["location"] == "Giardini Luzzati"
    assert event["category"] == "theatre-performance"
    assert event["category_confidence"] == 0.95
    assert "structured_event_metadata" in event["evidence_note"]


@pytest.mark.parametrize("fixture", ["luzzati-detail-ambiguous.html", "luzzati-detail-missing.html"])
def test_detail_ambiguous_or_missing_facts_stay_null(fixture):
    from scripts.collect_genova_luzzati import parse_detail

    html = (FIXTURE.parent / fixture).read_text(encoding="utf-8")
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["start_time"] is None
    assert event["end_time"] is None
    assert event["location"] is None
    assert event["category"] is None
    assert event["review_status"] == "needs_review"


def test_collection_sequentially_checks_only_the_requested_detail_cap():
    body = (
        '<ul><li class="product"><a href="/prodotto/one/"><h2>One</h2></a></li>'
        '<li class="product"><a href="/prodotto/two/"><h2>Two</h2></a></li>'
        '<li class="product"><a href="/prodotto/three/"><h2>Three</h2></a></li></ul>'
    ).encode()
    detail = (FIXTURE.parent / "luzzati-detail-text.html").read_bytes()
    missing = (FIXTURE.parent / "luzzati-detail-missing.html").read_bytes()
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, url, b"User-agent: *\nAllow: /\n")
        if url == INDEX_URL:
            return FakeResponse(200, url, body)
        return FakeResponse(200, url, detail if url.endswith("/one/") else missing)

    result = collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=2)
    assert calls == [
        "https://www.spazio-comune.org/robots.txt", INDEX_URL,
        "https://www.spazio-comune.org/prodotto/one/",
        "https://www.spazio-comune.org/prodotto/two/",
    ]
    assert result["access"]["request_count"] == 4
    assert result["access"]["detail_pages_checked"] == 2
    assert result["diagnostics"]["distinct_candidate_urls"] == 3
    assert len([event for event in result["events"] if event["start_time"]]) == 2
    assert all(event["review_status"] == "needs_review" for event in result["events"])


def test_collection_stops_before_a_disallowed_detail_path():
    body = '<li class="product"><a href="/prodotto/one/"><h2>One</h2></a></li>'.encode()
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, url, b"User-agent: *\nDisallow: /prodotto/\n")
        return FakeResponse(200, url, body)

    with pytest.raises(ProbeSkipped, match="detail path"):
        collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=1)
    assert calls == ["https://www.spazio-comune.org/robots.txt", INDEX_URL]


def test_collection_stops_after_detail_page_rate_limit():
    body = '<li class="product"><a href="/prodotto/one/"><h2>One</h2></a></li><li class="product"><a href="/prodotto/two/"><h2>Two</h2></a></li>'.encode()
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return FakeResponse(200, url, b"User-agent: *\nAllow: /\n")
        if url == INDEX_URL:
            return FakeResponse(200, url, body)
        return FakeResponse(429, url)

    with pytest.raises(ProbeSkipped, match="rate-limited"):
        collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=2)
    assert calls == [
        "https://www.spazio-comune.org/robots.txt", INDEX_URL,
        "https://www.spazio-comune.org/prodotto/one/",
    ]


def test_detail_limit_rejects_values_above_the_hard_cap_before_fetching():
    calls = []
    with pytest.raises(ProbeSkipped, match="between 0 and 12"):
        collect(active_source(), get=lambda url: calls.append(url), detail_page_limit=13)
    assert calls == []


def test_detail_page_metadata_is_used_when_jsonld_is_absent():
    from scripts.collect_genova_luzzati import parse_detail

    html = (FIXTURE.parent / "luzzati-detail-meta.html").read_text(encoding="utf-8")
    event = parse_detail(html, _detail_index_event(), 51)[0]
    assert event["start_time"] == "2026-10-14T19:30:00+02:00"
    assert event["end_time"] == "2026-10-14T21:00:00+02:00"
    assert event["location"] == "Giardini Luzzati"
    assert event["category"] == "music"
    assert event["category_confidence"] == 0.95
    assert "page_metadata" in event["evidence_note"]


@pytest.mark.parametrize(('date', 'expected_times'), [
    ('Venerdì 9 ottobre alle ore 18.00', ['18:00']),
    ('Giovedì 11 settembre, ore 20.00 e ore 20.30', ['20:00', '20:30']),
])
def test_diagnostics_preserve_yearless_dates_without_inventing_timestamps(date, expected_times):
    from scripts.collect_genova_luzzati import parse_detail
    diagnostic = {}
    events = parse_detail(f'<main><h1>Prova</h1><p>{date}</p></main>', _detail_index_event(), 51, diagnostics=diagnostic)
    assert all(event['start_time'] is None for event in events)
    assert diagnostic['explicit_years'] == []
    assert diagnostic['local_times'] == expected_times
    assert diagnostic['precision'] == 'unknown_year'
    assert 'year_missing' in diagnostic['unresolved_reasons']
    assert diagnostic['date_time_methods'] == ['visible_event_text']
    assert all('description' not in event for event in events)


def test_nested_div_does_not_end_event_scope_before_category_text():
    from scripts.collect_genova_luzzati import parse_detail
    html = '<div class="product"><div><h1>Prova</h1></div><p>Presentazione del libro.</p></div><footer>Comunità, socialità, giochi.</footer>'
    diagnostic = {}
    event = parse_detail(html, _detail_index_event(), 51, diagnostics=diagnostic)[0]
    assert event['category'] == 'talks-workshops'
    assert diagnostic['categories'] == ['talks-workshops']
    assert diagnostic['category_methods'] == ['title_or_description_keywords']


def test_diagnostics_distinguish_cap_skips_missing_fields_and_missing_title():
    body = b'<li class="product"><a href="/prodotto/one/"><h2>One</h2></a></li><li class="product"><a href="/prodotto/two/"><h2>Two</h2></a></li><a href="/prodotto/untitled/"></a>'
    def get(url):
        if url.endswith('/robots.txt'):
            return FakeResponse(200, url, b'User-agent: *\nAllow: /\n')
        return FakeResponse(200, url, body if url == INDEX_URL else b'<main><h1>One</h1></main>')
    result = collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=1)
    rows = result['diagnostics']['candidates']
    assert len(rows) == 3
    assert rows[0]['coverage'] == 'detail_fetched'
    assert rows[0]['http_status'] == 200
    assert 'no_date_on_page' in rows[0]['fields']['unresolved_reasons']
    assert rows[1]['unresolved_reasons'] == ['not_fetched_cap']
    assert rows[2]['unresolved_reasons'] == ['title_missing']


def test_failed_detail_keeps_diagnostics_and_stops_remaining_requests():
    body = b'<li class="product"><a href="/prodotto/one/"><h2>One</h2></a></li><li class="product"><a href="/prodotto/two/"><h2>Two</h2></a></li>'
    calls = []
    def get(url):
        calls.append(url)
        if url.endswith('/robots.txt'):
            return FakeResponse(200, url, b'User-agent: *\nAllow: /\n')
        return FakeResponse(200, url, body) if url == INDEX_URL else FakeResponse(429, url)
    with pytest.raises(ProbeSkipped) as caught:
        collect(active_source(), get=get, sleeper=lambda _: None, detail_page_limit=2)
    assert len(calls) == 3
    report = caught.value.report
    assert report['status'] == 'skipped'
    assert report['diagnostics']['candidates'][0]['unresolved_reasons'] == ['rate_limited']
    assert report['diagnostics']['candidates'][1]['unresolved_reasons'] == ['stopped_after_failure']
    from scripts.persist_genova_luzzati_report import validate_report
    with pytest.raises(ValueError, match='successful'):
        validate_report(report)


def test_diagnostics_show_complete_rome_time_and_ambiguous_dates():
    from scripts.collect_genova_luzzati import parse_detail
    diagnostic = {}
    parse_detail((FIXTURE.parent / 'luzzati-detail-text.html').read_text(), _detail_index_event(), 51, diagnostics=diagnostic)
    assert diagnostic['normalized_starts'][0] == '2026-10-06T18:00:00+02:00'
    assert diagnostic['explicit_years'] == [2026]
    assert diagnostic['precision'] == 'time'
    assert diagnostic['locations'] == ['Giardini Luzzati - Spazio Comune']
    parse_detail((FIXTURE.parent / 'luzzati-detail-ambiguous.html').read_text(), _detail_index_event(), 51, diagnostics=diagnostic)
    assert diagnostic['normalized_starts'] == []
    assert 'ambiguous_dates' in diagnostic['unresolved_reasons']
