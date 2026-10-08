# Giardini Luzzati bounded source adapter

The Luzzati pilot remains manual and source-approval gated. It reads the active index from the existing `feeds` registry, checks `robots.txt`, makes one index request, then checks a capped number of event detail pages sequentially.

## Request budget and scope

- Default: one robots request, one event-index request, and at most two detail-page requests, in that order.
- The manual workflow accepts an explicit `detail_page_limit` from 0 to 12. The absolute maximum is 14 HTTP requests per run: robots + index + twelve details.
- Before each detail request, the collector checks the exact HTTPS path against the publisher's robots rules. It only follows same-host `/prodotto/` links found on the index. It does not paginate, follow unrelated/off-host links, fetch poster images, or run OCR.
- Requests are sequential and wait for the published crawl delay (up to the existing 120-second safety limit). A disallowed path, rate limit, non-200 response, cross-host redirect, oversized response, or network failure stops the run before facts are persisted. There is no recurring schedule.
- The workflow preflights the Issue #87 migration, which records the per-run limit, detail pages checked, and total request count. A run requires that migration to be applied first.

## Facts and review

Structured event metadata is preferred, followed by visible event-page text. The collector emits only title, date/time normalized to `Europe/Rome`, venue when explicit, one exact-match project category when supported, publisher, original URL, stable occurrence identity, a category confidence, and a short evidence-source label. Separate showtimes remain separate occurrences. Missing or ambiguous facts remain null; every new fact remains `needs_review`.

Evidence labels identify only the source type (for example, structured metadata or visible page text); they do not copy source prose. The report and persistence SQL do not retain HTML, descriptions, image URLs, poster bytes, cookies, or response bodies. Poster-only dates are not inferred in this issue; they remain unknown.

Offline fixtures cover text extraction, structured metadata, multiple showtimes, missing/ambiguous fields, robots restrictions, request caps, and sequential order. Those fixtures do not replace the owner-reviewed live check of the first two pages. Run the workflow manually after the request-budget migration is applied; inspect the private review rows before publication.

## Persistence boundary

The adapter writes only through the guarded pilot workflow into `genova_event_facts` and `genova_source_scans`. Collected facts default to `needs_review`; publication still requires admin review, a known start time, and an active approved source. Failed scans do not delete prior facts.
