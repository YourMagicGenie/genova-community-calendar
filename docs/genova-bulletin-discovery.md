# Monthly bulletin PDF discovery

`scripts/discover_genova_bulletin_pdf.py` identifies likely monthly PDF links
from a source page. Its offline CLI reads a page fixture and emits a candidate
record without making a request:

```sh
python scripts/discover_genova_bulletin_pdf.py \
  --fixture-html tests/fixtures/genova_bulletin_links/matching.html \
  --source-name 'Example events' \
  --page-url 'https://events.example.org/calendar/' \
  --month 2026-10
```

The result preserves the source name, page and PDF URLs, detected month,
selection evidence, and retrieval timestamp. Stale, absent, and multiple
current-month links are returned as `no_match` or `ambiguous`, with no PDF URL
selected. Discovery never downloads the PDF.

The live helper accepts only a trusted active-source snapshot from the
existing guarded source workflow. It checks `robots.txt`, honors the published
crawl delay within the probe limit, caps work at two requests (robots plus one
page), and fails closed for an inactive source, blocked path, unavailable
robots/page, or cross-host redirect. It does not fetch the candidate PDF.
There is deliberately no command that accepts an arbitrary JSON file as proof
of source approval.

The four checked-in HTML pages are synthetic fixtures. Visit Genoa remains a
candidate: do not call the live helper for it until a maintainer has explicitly
approved and activated it in the source registry. The uploaded October PDF is
not used as discovery input.

Run the focused tests with:

```sh
pytest tests/test_discover_genova_bulletin_pdf.py -v
```
