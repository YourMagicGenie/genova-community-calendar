# Giardini Luzzati bounded source adapter

Issue #51's first collector is intentionally narrower than a production crawler.

- It reads the exact Giardini Luzzati index source from the existing `feeds` registry and requires `status=active`. If approval state cannot be read, it makes no publisher request.
- It checks `robots.txt` for the exact verified index path and then makes at most one index-page GET.
- It never follows event links. The index parser identifies same-host `/prodotto/` anchors, associates them with nearby product/event cards across common `li`, `div`, and `article` layouts, then emits only title, listed Europe/Rome date/time, listed venue, publisher, direct event URL, normalized URL, stable source identity, and review placeholders.
- Missing date/time/location remain null. Multiple explicitly listed showtimes become separate occurrences.
- Output is facts-only JSON for the persistence/review slice. It includes aggregate parser diagnostics (qualifying links, distinct candidate URLs, formed records, titles, dates, and times) so a zero-event result is diagnosable. No HTML, description, image, cookie, or response body is retained.
- There is no schedule. After offline parser work is merged, any live verification remains a separate manual run, limited to robots plus at most one index request.

The offline fixtures cover the original list-style card, div/article theme cards, repeated title/thumbnail links, missing facts, ignored off-host/non-product links, an empty index, and a candidate record with no title. They exercise the parser contract without claiming that every field appears on the current live index.

## Persistence boundary

The next Issue #51 slice adds `genova_event_facts` and `genova_source_scans` rather than writing directly into the inherited raw `events` table. Luzzati remains registered in the existing `feeds` source registry. Collected facts default to `needs_review`; only an admin may review them, and a publication guard requires a known start time and an active approved source. Anonymous visitors receive only the field-limited output of `list_public_genova_events()`. Failed scans have their own provenance rows and do not delete previously collected facts.
