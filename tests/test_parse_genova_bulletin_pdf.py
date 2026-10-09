import json
import subprocess
import sys
from pathlib import Path

from scripts.parse_genova_bulletin_pdf import _date_facts, parse_pdf


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "genova_bulletin_synthetic.pdf"


def test_synthetic_two_column_pdf_extracts_independent_review_candidates():
    candidates = parse_pdf(FIXTURE)

    assert [candidate["title"] for candidate in candidates] == [
        "Concerto jazz al Porto Antico",
        "Mostra di ceramiche",
        "Concerto acustico",
        "Esposizione fotografica",
        "Visita guidata al museo",
    ]
    assert candidates[0]["start_date"] == "2026-10-10"
    assert candidates[0]["time"] == "18:30"
    assert candidates[0]["timezone"] == "Europe/Rome"
    assert candidates[0]["section"] == "MUSICA"
    assert candidates[0]["category_suggestions"][0]["category"] == "music"
    assert candidates[0]["review_status"] == "needs_review"

    # The two printed performances stay separate instead of expanding dates.
    assert candidates[2]["start_date"] == "2026-10-11"
    assert candidates[2]["time"] == "20:00"


def test_ranges_end_only_missing_time_and_weekday_schedules_remain_explicit():
    candidates = parse_pdf(FIXTURE)
    exhibition = candidates[1]
    assert (exhibition["start_date"], exhibition["end_date"]) == ("2026-10-04", "2026-10-06")
    assert exhibition["time"] is None
    assert "start time not stated" in exhibition["unresolved_reasons"]

    end_only = candidates[3]
    assert end_only["start_date"] is None
    assert end_only["end_date"] == "2026-10-09"
    assert "start date not stated" in end_only["unresolved_reasons"]

    weekday = candidates[4]
    assert weekday["date_precision"] == "weekday_only"
    assert weekday["start_date"] is None
    assert weekday["time"] == "15:00"
    assert weekday["timezone"] is None


def test_yearless_and_listed_dates_keep_only_supported_values():
    yearless = _date_facts("dal 4 al 6 ottobre", None, None)
    assert yearless["precision"] == "yearless"
    assert yearless["start_date"] is None
    assert yearless["partial_dates"] == [{"day": 4, "month": 10}, {"day": 6, "month": 10}]

    listed = _date_facts("10 e 11 ottobre 2026", 10, 2026)
    assert listed["precision"] == "listed_dates"
    assert listed["dates"] == ["2026-10-10", "2026-10-11"]


def test_candidate_evidence_and_cli_json_are_stable_and_source_attributed():
    candidates = parse_pdf(FIXTURE)
    assert candidates[0]["source_document"] == FIXTURE.name
    assert candidates[0]["source_page"] == 1
    assert candidates[0]["field_evidence"]["date"]["text"] == "10 ottobre 2026"
    assert candidates[0]["field_evidence"]["date"]["bbox"] == candidates[0]["source_bbox"]

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "parse_genova_bulletin_pdf.py"), str(FIXTURE)],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == candidates
