# Preparing private bulletin candidates for review

`scripts/prepare_genova_bulletin_import.py` maps normalized PDF parser output
into a bounded SQL call for the private event-facts importer. It performs no
network request and does not execute the SQL:

```sh
python scripts/parse_genova_bulletin_pdf.py /path/to/bulletin.pdf > candidates.json
python scripts/prepare_genova_bulletin_import.py \
  --source trusted-active-source.json \
  --discovery current-bulletin-discovery.json \
  --candidates candidates.json \
  --output bulletin-review-import.sql
```

The prepared payload keeps parser facts in `needs_review`, records stable
candidate IDs, and carries source page/bounding-box evidence, parser version,
retrieval time, date precision, partial date clues, and unresolved reasons.
Only a complete, unambiguous calendar date plus an explicit, non-ambiguous
Europe/Rome time becomes a timestamp. Date-only, multi-day, end-only,
yearless, and weekday-only entries remain without a start timestamp; they are
not converted into guessed all-day or recurring events. Explicitly listed
performance dates become separate candidates. Title-less candidates are
reported as skipped.

The SQL function verifies that the supplied feed ID and source page still
match an active Genova feed before it accepts facts. It assigns the publisher
label from that database row and forces `needs_review`; the public event
function does not expose those records. The database rechecks state when the
SQL is run, so a locally supplied source snapshot alone cannot authorize an
inactive source. The function is executable only by `service_role`.

The importer is a persistence building block, not the complete live workflow.
The trusted source lookup, approved PDF retrieval, admin evidence display,
hosted migration setup, and any publication remain separate guarded steps.
Do not execute generated SQL against the hosted project as part of a fixture
test.

Run the focused test with:

```sh
pytest tests/test_prepare_genova_bulletin_import.py -v
```
