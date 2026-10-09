import copy
import json
from pathlib import Path

import pytest

from scripts.collect_genova_luzzati import parse_index
from scripts.persist_genova_luzzati_report import INDEX_URL, render_sql, validate_report


FIXTURE = Path(__file__).parent / "fixtures" / "genova" / "luzzati-index.html"
REVISION = "0123456789abcdef0123456789abcdef01234567"


def report():
    events = parse_index(FIXTURE.read_text(encoding="utf-8"), 51)
    return {
        "status": "ok",
        "source": {
            "id": 51,
            "name": "Giardini Luzzati / Spazio Comune",
            "url": INDEX_URL,
            "publisher_url": "https://www.spazio-comune.org/",
        },
        "access": {
            "robots_http_status": 200,
            "robots_decision": "allowed",
            "page_http_status": 200,
            "request_count": 2,
            "detail_page_limit": 2,
            "detail_pages_checked": 0,
            "crawl_delay_seconds": 0,
        },
        "events": events,
        "events_found": len(events),
        "events_needing_review": len(events),
    }


def test_report_validation_accepts_unknown_fields_and_separate_occurrences():
    value = report()
    validate_report(value)
    assert any(event["start_time"] is None for event in value["events"])
    assert all(isinstance(event["is_all_day"], bool) for event in value["events"])
    assert len([event for event in value["events"] if event["title"] == "Doppio turno"]) == 2
    assert all(event["category_suggestions"] for event in value["events"])


def test_persistence_sql_appends_scan_and_upserts_without_delete_or_publish():
    sql = render_sql(report(), REVISION)
    assert "INSERT INTO public.genova_source_scans" in sql
    assert "SELECT public.import_genova_luzzati_facts" in sql
    assert "payload -> 'events'" in sql
    assert "DELETE FROM public.genova_event_facts" not in sql
    assert "review_status = EXCLUDED.review_status" not in sql
    import base64, re
    encoded = re.search(r"decode\('([^']+)', 'base64'\)", sql).group(1)
    assert json.loads(base64.b64decode(encoded)) == report()
    assert "detail_page_limit, detail_pages_checked" in sql
    assert "COMMIT;" in sql


@pytest.mark.parametrize("mutation", ["wrong_source", "blocked", "too_many_requests", "foreign_host", "published", "invalid_suggestion", "invalid_all_day"])
def test_report_validation_fails_closed(mutation):
    value = copy.deepcopy(report())
    if mutation == "wrong_source":
        value["source"]["url"] = "https://example.org/events/"
    elif mutation == "blocked":
        value["access"]["robots_decision"] = "disallowed"
    elif mutation == "too_many_requests":
        value["access"]["request_count"] = 15
    elif mutation == "foreign_host":
        value["events"][0]["url"] = "https://example.org/event/"
    elif mutation == "published":
        value["events"][0]["review_status"] = "published"
    elif mutation == "invalid_suggestion":
        value["events"][0]["category_suggestions"] = [{
            "category": "date-night", "confidence": 0.9, "evidence": "unsupported tag as category",
        }]
    elif mutation == "invalid_all_day":
        value["events"][0]["is_all_day"] = "true"

    with pytest.raises(ValueError):
        validate_report(value)


@pytest.mark.parametrize("mutation", ["bad_partial_date", "incomplete_with_timestamp", "oversized_evidence", "missing_metadata"])
def test_report_rejects_malformed_or_unbounded_source_metadata(mutation):
    value = copy.deepcopy(report())
    event = value["events"][0]
    if mutation == "bad_partial_date":
        event["source_metadata"]["partial_dates"] = [{"day": 31, "month": 2}]
    elif mutation == "incomplete_with_timestamp":
        event["source_metadata"].update(date_precision="yearless", partial_dates=[{"day": 9, "month": 10}])
        event["start_time"] = "2026-10-09T18:00:00+02:00"
    elif mutation == "oversized_evidence":
        event["source_metadata"]["field_evidence"] = {"date": {"text": "x" * 241, "method": "visible_event_text"}}
    else:
        del event["source_metadata"]
    with pytest.raises(ValueError):
        validate_report(value)


def test_luzzati_and_bulletin_metadata_share_the_review_evidence_core():
    website = report()["events"][0]["source_metadata"]
    bulletin = {
        "kind": "monthly_bulletin_pdf", "field_evidence": {}, "unresolved_reasons": [],
        "date_precision": "yearless", "partial_dates": [{"day": 9, "month": 10}],
        "bulletin_url": "https://www.visitgenoa.it/october.pdf", "source_page": 2,
        "source_bbox": [10, 10, 20, 20],
    }
    shared = {"field_evidence", "unresolved_reasons", "date_precision", "partial_dates"}
    assert shared <= website.keys()
    assert shared <= bulletin.keys()


def test_renderer_rejects_non_commit_revision():
    with pytest.raises(ValueError, match="full Git commit"):
        render_sql(report(), "main")
