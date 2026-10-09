from copy import deepcopy
from pathlib import Path

import pytest

from scripts.parse_genova_bulletin_pdf import parse_pdf
from scripts.prepare_genova_bulletin_import import (
    PARSER_VERSION,
    _local_timestamp,
    prepare_import,
    render_sql,
)


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_PDF = ROOT / "tests" / "fixtures" / "genova_bulletin_synthetic.pdf"
SOURCE = {
    "id": 42,
    "city": "genova",
    "status": "active",
    "url": "https://events.example.org/calendar/",
    "name": "Example events",
}
DISCOVERY = {
    "status": "found",
    "page_url": SOURCE["url"],
    "pdf_url": "https://events.example.org/files/ottobre-2026.pdf",
    "retrieval_timestamp": "2026-10-09T12:00:00+00:00",
}


def test_parser_candidates_map_with_evidence_and_only_complete_timestamps():
    rows = parse_pdf(SYNTHETIC_PDF)
    report = prepare_import(SOURCE, DISCOVERY, rows)
    assert len(report["events"]) == 5
    first, exhibition, second, end_only, weekday = report["events"]

    assert first["start_time"] == "2026-10-10T18:30+02:00"
    assert first["normalized_url"] == DISCOVERY["pdf_url"]
    assert first["source_uid"].startswith("genova-bulletin:")
    assert first["category_suggestions"][0]["category"] == "music"
    assert first["field_evidence"]["date"]["text"] == "10 ottobre 2026"
    assert first["start_date_candidate"] == "2026-10-10"

    assert exhibition["start_time"] is None
    assert exhibition["date_precision"] == "range"
    assert exhibition["start_date_candidate"] == "2026-10-04"
    assert exhibition["end_date_candidate"] == "2026-10-06"
    assert second["start_time"] == "2026-10-11T20:00+02:00"
    assert end_only["start_time"] is None
    assert weekday["start_time"] is None
    assert weekday["unresolved_reasons"]


def test_repeat_runs_have_stable_candidate_identity_and_sql_is_review_only():
    rows = parse_pdf(SYNTHETIC_PDF)
    first = prepare_import(SOURCE, DISCOVERY, rows)
    again = prepare_import(SOURCE, DISCOVERY, rows)
    assert [event["source_uid"] for event in first["events"]] == [event["source_uid"] for event in again["events"]]
    sql = render_sql(first)
    assert "public.import_genova_bulletin_facts" in sql
    assert "review_status" not in sql
    assert "COMMIT;" in sql
    assert first["parser_version"] == PARSER_VERSION


def test_listed_performances_expand_to_separate_rows_and_dst_times_stay_unresolved():
    candidate = {
        "title": "Serata musicale",
        "start_date": None,
        "end_date": None,
        "dates": ["2099-01-12", "2099-01-13"],
        "partial_dates": [],
        "date_precision": "listed_dates",
        "time": "18:00",
        "venue": None,
        "category_suggestions": [],
        "source_page": 1,
        "source_bbox": [1, 2, 10, 20],
        "field_evidence": {"date": {"page": 1, "bbox": [1, 2, 10, 20], "text": "12 e 13 gennaio 2099"}},
        "unresolved_reasons": [],
        "review_status": "needs_review",
    }
    rows = prepare_import(SOURCE, DISCOVERY, [candidate])["events"]
    assert len(rows) == 2
    assert rows[0]["source_uid"] != rows[1]["source_uid"]
    assert all(row["start_time"] is not None for row in rows)
    assert _local_timestamp("2026-10-25", "02:30") is None
    assert _local_timestamp("2026-03-29", "02:30") is None


def test_unapproved_ambiguous_or_mismatched_source_inputs_fail_closed():
    with pytest.raises(ValueError, match="trusted active"):
        prepare_import({**SOURCE, "status": "pending"}, DISCOVERY, [])
    with pytest.raises(ValueError, match="unambiguous"):
        prepare_import(SOURCE, {**DISCOVERY, "status": "ambiguous"}, [])
    with pytest.raises(ValueError, match="does not match"):
        prepare_import(SOURCE, {**DISCOVERY, "page_url": "https://other.example.org/"}, [])


def test_titleless_candidates_are_skipped_but_source_metadata_is_bounded():
    candidate = {
        "title": None,
        "review_status": "needs_review",
        "source_page": 1,
        "source_bbox": [1, 2, 3, 4],
        "field_evidence": {},
    }
    report = prepare_import(SOURCE, DISCOVERY, [candidate])
    assert report["events"] == []
    assert report["skipped_candidates"] == 1

    candidate["title"] = "Too much evidence"
    candidate["field_evidence"] = {"title": "x" * 9000}
    with pytest.raises(ValueError, match="field-level evidence"):
        prepare_import(SOURCE, DISCOVERY, [candidate])
