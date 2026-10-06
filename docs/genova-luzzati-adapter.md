# Giardini Luzzati bounded source adapter

Issue #51's first collector is intentionally narrower than a production crawler.

- It reads the exact Giardini Luzzati index source from the existing `feeds` registry and requires `status=active`. If approval state cannot be read, it makes no publisher request.
- It checks `robots.txt` for the exact verified index path and then makes at most one index-page GET.
- It never follows event links. The index parser emits only title, listed Europe/Rome date/time, listed venue, publisher, direct event URL, normalized URL, stable source identity, and review placeholders.
- Missing date/time/location remain null. Multiple explicitly listed showtimes become separate occurrences.
- Output is facts-only JSON for the next persistence/review slice. No HTML, description, image, cookie, or response body is retained.
- There is no schedule. The live Issue #50 verification already used today's source request budget, so this adapter must not be live-run again on 2026-10-06.

The offline fixture is representative of the parser contract; it is not a claim that every field appears on the current live index.

## Persistence boundary

The next Issue #51 slice adds `genova_event_facts` and `genova_source_scans` rather than writing directly into the inherited raw `events` table. Luzzati remains registered in the existing `feeds` source registry. Collected facts default to `needs_review`; only an admin may review them, and a publication guard requires a known start time and an active approved source. Anonymous visitors receive only the field-limited output of `list_public_genova_events()`. Failed scans have their own provenance rows and do not delete previously collected facts.
