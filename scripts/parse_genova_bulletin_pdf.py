#!/usr/bin/env python3
"""Extract reviewable facts from text-based Genova bulletin PDFs, offline."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pdfplumber

# Make both `python scripts/parse_genova_bulletin_pdf.py` and `python -m`
# resolve the shared helper from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.genova_taxonomy import suggest_categories


MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5,
    "giugno": 6, "luglio": 7, "agosto": 8, "settembre": 9,
    "ottobre": 10, "novembre": 11, "dicembre": 12,
}
WEEKDAYS = (
    "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica",
)
TIME_RE = re.compile(r"(?i)\b(?:ore|h\.?|alle)\s*(\d{1,2})(?:[:.](\d{2}))?\b")
MONTH_DATE_RE = re.compile(
    r"(?i)\b(?P<days>\d{1,2}(?:\s*(?:,|e|&)\s*\d{1,2})*)\s+"
    r"(?P<month>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)(?:\s+(?P<year>20\d{2}))?\b"
)
NUMERIC_DATE_RE = re.compile(r"\b(?P<day>\d{1,2})[/.](?P<month>\d{1,2})(?:[/.](?P<year>\d{2,4}))?\b")
RANGE_RE = re.compile(
    r"(?i)\bdal\s+(?P<start>\d{1,2})\s+(?:al|all['’])\s+(?P<end>\d{1,2})\s+"
    r"(?P<month>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)(?:\s+(?P<year>20\d{2}))?\b"
)
END_ONLY_RE = re.compile(
    r"(?i)\bfino\s+al\s+(?P<day>\d{1,2})\s+"
    r"(?P<month>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)(?:\s+(?P<year>20\d{2}))?\b"
)


@dataclass
class TextBlock:
    page: int
    column: int
    bbox: tuple[float, float, float, float]
    lines: list[str]

    @property
    def text(self) -> str:
        return " ".join(self.lines).strip()


def _fold(value: str) -> str:
    return value.casefold().replace("ì", "i").replace("’", "'")


def _pdf_blocks(page, page_number: int) -> list[TextBlock]:
    """Read word coordinates, group lines, then keep each page column ordered."""
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
    if not words:
        return []
    page_mid = float(page.width) / 2
    def word_column(word):
        return 0 if (word["x0"] + word["x1"]) / 2 < page_mid else 1

    line_groups: list[list[dict]] = []
    for word in sorted(words, key=lambda item: (word_column(item), item["top"], item["x0"])):
        same_column = bool(line_groups) and word_column(word) == word_column(line_groups[-1][0])
        if same_column and abs(word["top"] - line_groups[-1][0]["top"]) <= 3:
            line_groups[-1].append(word)
        else:
            line_groups.append([word])

    lines = []
    for group in line_groups:
        group.sort(key=lambda item: item["x0"])
        left, top = min(w["x0"] for w in group), min(w["top"] for w in group)
        right, bottom = max(w["x1"] for w in group), max(w["bottom"] for w in group)
        # Assign full-width headers by their starting x position; ordinary
        # bulletin content remains ordered within its visual column.
        column = word_column(group[0])
        lines.append((column, top, (left, top, right, bottom), " ".join(w["text"] for w in group)))

    blocks: list[TextBlock] = []
    for column in (0, 1):
        selected = [line for line in lines if line[0] == column]
        selected.sort(key=lambda line: line[1])
        current: list[tuple[int, float, tuple[float, float, float, float], str]] = []
        for line in selected:
            if current and line[1] - current[-1][1] > 14:
                blocks.append(_make_block(current, page_number, column))
                current = []
            current.append(line)
        if current:
            blocks.append(_make_block(current, page_number, column))
    return sorted(blocks, key=lambda block: (block.page, block.bbox[1], block.column))


def _make_block(lines, page_number: int, column: int) -> TextBlock:
    return TextBlock(
        page=page_number,
        column=column,
        bbox=(min(row[2][0] for row in lines), min(row[2][1] for row in lines),
              max(row[2][2] for row in lines), max(row[2][3] for row in lines)),
        lines=[row[3] for row in lines],
    )


def _month_context(text: str) -> tuple[int | None, int | None]:
    contexts = set()
    for match in re.finditer(
        r"(?i)\b(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
        r"settembre|ottobre|novembre|dicembre)\s+(20\d{2})\b", text,
    ):
        contexts.add((MONTHS[match.group(1).casefold()], int(match.group(2))))
    return next(iter(contexts)) if len(contexts) == 1 else (None, None)


def _iso(day: int, month: int, year: int | None) -> str | None:
    if year is None:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _date_facts(text: str, context_month: int | None, context_year: int | None) -> dict:
    folded = _fold(text)
    range_match = RANGE_RE.search(folded)
    if range_match:
        month = MONTHS[range_match.group("month")]
        year = int(range_match.group("year")) if range_match.group("year") else context_year
        start = _iso(int(range_match.group("start")), month, year)
        end = _iso(int(range_match.group("end")), month, year)
        if start and end:
            return {"start_date": start, "end_date": end, "dates": [], "partial_dates": [], "precision": "range", "raw": range_match.group(0)}
        precision = "yearless" if year is None else "unresolved"
        partial_dates = ([{"day": int(range_match.group("start")), "month": month},
                          {"day": int(range_match.group("end")), "month": month}] if year is None else [])
        return {"start_date": None, "end_date": None, "dates": [], "partial_dates": partial_dates,
                "precision": precision, "raw": range_match.group(0)}

    end_match = END_ONLY_RE.search(folded)
    if end_match:
        month = MONTHS[end_match.group("month")]
        year = int(end_match.group("year")) if end_match.group("year") else context_year
        end_date = _iso(int(end_match.group("day")), month, year)
        return {
            "start_date": None, "end_date": end_date,
            "dates": [], "partial_dates": ([{"day": int(end_match.group("day")), "month": month}]
                                              if year is None else []),
            "precision": "end_only", "raw": end_match.group(0),
        }

    found = []
    partial = []
    for match in MONTH_DATE_RE.finditer(folded):
        month = MONTHS[match.group("month")]
        year = int(match.group("year")) if match.group("year") else (context_year if context_month == month else None)
        days = [int(value) for value in re.findall(r"\d{1,2}", match.group("days"))]
        for day in days:
            parsed = _iso(day, month, year)
            if parsed:
                found.append((parsed, match.group(0)))
            elif year is None and 1 <= day <= 31:
                partial.append({"day": day, "month": month})
    for match in NUMERIC_DATE_RE.finditer(folded):
        month = int(match.group("month"))
        raw_year = match.group("year")
        year = int(raw_year) if raw_year else (context_year if context_month == month else None)
        if year is not None and year < 100:
            year += 2000
        parsed = _iso(int(match.group("day")), month, year)
        if parsed:
            found.append((parsed, match.group(0)))
        elif year is None and 1 <= int(match.group("day")) <= 31 and 1 <= month <= 12:
            partial.append({"day": int(match.group("day")), "month": month})
    if found:
        unique_dates = list(dict.fromkeys(item[0] for item in found))
        raw = "; ".join(dict.fromkeys(item[1] for item in found))
        if len(unique_dates) == 1:
            return {"start_date": unique_dates[0], "end_date": None, "dates": [], "partial_dates": [], "precision": "day", "raw": raw}
        return {"start_date": None, "end_date": None, "dates": unique_dates, "partial_dates": [], "precision": "listed_dates", "raw": raw}

    if partial:
        raw_values = [match.group(0) for pattern in (MONTH_DATE_RE, NUMERIC_DATE_RE) for match in pattern.finditer(folded)]
        return {"start_date": None, "end_date": None, "dates": [], "partial_dates": partial,
                "precision": "yearless", "raw": "; ".join(dict.fromkeys(raw_values))}

    weekday_match = next((weekday for weekday in WEEKDAYS if re.search(r"(?<!\w)" + weekday + r"(?!\w)", folded)), None)
    if weekday_match:
        return {"start_date": None, "end_date": None, "dates": [], "partial_dates": [], "precision": "weekday_only", "raw": weekday_match}
    return {"start_date": None, "end_date": None, "dates": [], "partial_dates": [], "precision": "unknown", "raw": None}


def _time_fact(text: str) -> tuple[str | None, str | None]:
    match = TIME_RE.search(text)
    if not match:
        return None, None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        return None, match.group(0)
    return f"{hour:02d}:{minute:02d}", match.group(0)


def _is_heading(text: str) -> bool:
    compact = re.sub(r"[^\w]", "", text, flags=re.UNICODE)
    return bool(compact) and len(compact) <= 36 and compact == compact.upper() and not any(ch.isdigit() for ch in text)


def parse_pdf(path: str | Path) -> list[dict]:
    """Return review-only event candidates without network or persistence."""
    path = Path(path)
    with pdfplumber.open(path) as pdf:
        all_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        context_month, context_year = _month_context(all_text)
        candidates = []
        for page_number, page in enumerate(pdf.pages, start=1):
            section_by_column = {0: None, 1: None}
            for block in _pdf_blocks(page, page_number):
                text = block.text
                if _is_heading(text):
                    section_by_column[block.column] = text.strip()
                    continue
                dates = _date_facts(text, context_month, context_year)
                time_value, raw_time = _time_fact(text)
                if dates["precision"] == "unknown" and time_value is None:
                    continue
                # A date/time block is one source listing. Keep separately
                # printed listings separate; never expand a date range.
                title_lines = [line.strip(" •·-–—") for line in block.lines if line.strip()]
                title = next((line for line in title_lines if not _date_facts(line, context_month, context_year)["raw"]
                              and not TIME_RE.search(line) and not _is_heading(line)), None)
                venue_match = re.search(r"(?i)\b(?:luogo|sede|dove)\s*:\s*([^;,.]+)", text)
                venue = venue_match.group(1).strip() if venue_match else None
                unresolved = []
                if dates["precision"] == "end_only":
                    unresolved.append("start date not stated")
                elif dates["precision"] == "weekday_only":
                    unresolved.append("weekday schedule has no explicit calendar date")
                elif dates["precision"] in ("unknown", "unresolved"):
                    unresolved.append("explicit calendar date not resolved")
                elif dates["precision"] == "yearless":
                    unresolved.append("year not stated and no unique document year is available")
                if dates["partial_dates"] and dates["precision"] == "end_only":
                    unresolved.append("year not stated and no unique document year is available")
                if time_value is None:
                    unresolved.append("start time not stated")
                suggestions = suggest_categories(title=title, section=section_by_column[block.column], venue=venue)
                bbox = [round(value, 1) for value in block.bbox]
                evidence = {
                    "title": {"page": page_number, "bbox": bbox, "text": title} if title else None,
                    "date": {"page": page_number, "bbox": bbox, "text": dates["raw"]} if dates["raw"] else None,
                    "time": {"page": page_number, "bbox": bbox, "text": raw_time} if raw_time else None,
                    "venue": {"page": page_number, "bbox": bbox, "text": venue} if venue else None,
                    "section": {"page": page_number, "bbox": bbox, "text": section_by_column[block.column]} if section_by_column[block.column] else None,
                }
                candidates.append({
                    "title": title,
                    "start_date": dates["start_date"],
                    "end_date": dates["end_date"],
                    "dates": dates["dates"],
                    "partial_dates": dates["partial_dates"],
                    "date_precision": dates["precision"],
                    "time": time_value,
                    "timezone": "Europe/Rome" if dates["start_date"] and time_value else None,
                    "venue": venue,
                    "section": section_by_column[block.column],
                    "category_suggestions": suggestions,
                    "source_document": path.name,
                    "source_page": page_number,
                    "source_bbox": bbox,
                    "field_evidence": evidence,
                    "review_status": "needs_review",
                    "unresolved_reasons": unresolved,
                })
        return candidates


def _write_csv(rows: list[dict], output) -> None:
    fields = ["title", "start_date", "end_date", "dates", "partial_dates", "date_precision", "time", "timezone",
              "venue", "section", "category_suggestions", "source_document", "source_page",
              "source_bbox", "field_evidence", "review_status", "unresolved_reasons"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(row[key], ensure_ascii=False) if isinstance(row[key], (list, dict)) else row[key]
                         for key in fields})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="local text-based event bulletin PDF")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args(argv)
    try:
        rows = parse_pdf(args.pdf)
    except (OSError, pdfplumber.pdfminer.pdfdocument.PDFSyntaxError) as exc:
        print(f"could not read PDF: {exc}", file=sys.stderr)
        return 2
    if args.format == "csv":
        _write_csv(rows, sys.stdout)
    else:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
