# Teatro della Tosse bounded comparison

The adapter is a manual, read-only candidate-source comparison for #94. It does
not activate a feed, contact Supabase, import facts, publish events, or schedule
collection. Reports contain calendar facts and access diagnostics only. Source
HTML and descriptions exist only in memory and are never written to disk.

## Reproduce deliberately

Run `python scripts/collect_genova_tosse.py --sample-only --detail-limit 3 --output /tmp/tosse-comparison.json`
for the three fixed detail URLs. This costs one robots request and up to three
sequential detail requests. Without `--sample-only`, the fixed `/eventi/` index
is fetched once, followed by at most three unique same-host `.htm` detail URLs.
The manual **Genova Tosse bounded comparison** workflow defaults to sample-only
and retains its facts report for one day. There is no schedule. Do not rerun
index debugging on October 8: the earlier index probe already consumed today's
index check. Future deliberate index discovery is available through that workflow.

Robots denial, unavailable robots, excess crawl delay, unexpected redirects,
HTTP errors including 429, and responses exceeding 2 MB stop the run without
retry. Requests wait at least one second and honor published crawl delay. No
login, paywall bypass, external booking links, images, or OCR is needed here.

## What the parser accepts

Only explicit full `dd/mm/yyyy` dates and one `HH:MM` per **Programmazione** row
are accepted. It prefers table rows and supports the publisher's responsive
layout using consecutive full-date segments. It stops at **Altri spettacoli**;
page-description times, related events, index month/day badges, and date-range
headers are not used to invent showtimes. Multiple dates under one URL remain
separate occurrences with stable URL-plus-start identities. Missing years,
invalid dates, and ambiguous or nonexistent Rome local times stay unresolved.
Venues use a short supported-name list; unfamiliar names stay unknown. Category
inference currently recognizes explicit music words in the event title; other
categories remain unknown for human review.

## October 8, 2026 live comparison

A deliberate known-detail run made **four requests**: robots (200) plus three
details (200). It did not fetch the index again, activate a source, or persist
anything to the database. The responsive schedule parser produced:

| Page | Occurrences | Dates and local times | Venue | Category |
| --- | ---: | --- | --- | --- |
| [Il bancone confessionale](https://teatrodellatosse.it/eventi/il-bancone-confessionale.htm) | 1 | Oct 8, 2026 at 20:00 | Luzzati Lab | Unknown |
| [Genova Music Day](https://teatrodellatosse.it/eventi/genova-music-day.htm) | 1 | Oct 9, 2026 at 18:30 | La Claque | music |
| [A cena con Macbeth](https://teatrodellatosse.it/eventi/a-cena-con-macbeth.htm) | 10 | Oct 15–17 and 20–24 at 20:30; Oct 18 and 25 at 18:30 | Sala Aldo Trionfo | Unknown |

October 19 was correctly absent. October 25 normalized to `+01:00`; the other
October dates normalized to `+02:00`. All twelve starts are upcoming relative to
the run's UTC time. No inferred season year or archive filtering was needed.

| Metric | Luzzati full-detail pilot | Tosse known-detail comparison |
| --- | ---: | ---: |
| Detail URLs checked | 12 | 3 |
| Explicit full-date/time occurrences | 5 | 12 |
| Upcoming dated occurrences | 0 | 12 |
| Unknown-year detail pages | 7 | 0 |
| Locations found | 12 detail pages | 12 occurrences |
| Categories inferred | 9 detail pages | 1 occurrence |

These are differently selected samples, not a whole-source quality ranking.
Tosse's explicit schedule rows are a promising upcoming-date source; category
coverage is weak and index discovery still needs its first deliberate adapter
run on a later day. Keep Tosse inactive until source approval and persistence
are designed separately. Existing recurring collection and publication remain
disabled. Luzzati's richer title/description category extraction remains useful.

Synthetic tests cover table and responsive layouts, distinct showtimes,
duplicate rows, related-content exclusion, missing years/times, unknown venues,
invalid dates, DST, URL restrictions, request caps, robots denial, and 429 stop.
