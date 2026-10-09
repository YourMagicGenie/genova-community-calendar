# Offline event bulletin PDF parser

Use `scripts/parse_genova_bulletin_pdf.py` to extract candidate event facts from
a local, text-based PDF. It makes no network requests and has no database or
publishing integration.

```sh
python -m pip install -r requirements-dev.txt
python scripts/parse_genova_bulletin_pdf.py /path/to/bulletin.pdf > candidates.json
python scripts/parse_genova_bulletin_pdf.py /path/to/bulletin.pdf --format csv > candidates.csv
```

The parser uses PDF word coordinates to keep columns separate and attach page
and bounding-box evidence to extracted fields. It returns explicit dates,
Italian `dal … al …` ranges, end-only `fino al …` dates, supported time values,
and the section context used by the shared Genova category suggester. A unique
month/year printed in the document may complete a date from that month; the
filename is never treated as date evidence. Unsupported or ambiguous clues
remain partial and appear with a `needs_review` status and unresolved reasons.
Weekday-only schedules and end-only exhibition dates are never turned into a
guessed start date. Printed date ranges are kept as ranges; independently
printed performances remain separate candidates.

The checked-in PDF under `tests/fixtures/` is a small, test-authored synthetic
layout fixture. The uploaded Visit Genoa bulletin is not stored in the
repository. This parser currently supports text-based PDFs; image-only scans
need OCR and are out of scope. Extraction is a starting point for review, not
event approval or publication.

Run the focused regression tests with:

```sh
pytest tests/test_parse_genova_bulletin_pdf.py -v
```
