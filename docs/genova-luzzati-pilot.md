# Manual Giardini Luzzati pilot run

The first real-source import remains manual. The workflow **Run manual Giardini Luzzati pilot** has no schedule and uses the same `genova-supabase-bootstrap` environment already used for reviewed migrations.

Before it contacts the publisher, it verifies that migration `20261006124729_genova_first_source_persistence.sql` is present in hosted migration history. The same guarded database check writes a minimal approved-source JSON snapshot for the collector. The collector does not query the public Supabase Data API for source approval; that route is intentionally unavailable to browser roles after the security hardening. It validates the trusted snapshot, performs its bounded robots/index request, validates the facts-only report, and persists the result transactionally.

Persistence rules:

- append one private scan-provenance row;
- upsert occurrences by stable `source_uid`;
- refresh facts and `last_seen` only when the stored source ID and normalized URL still match;
- preserve the existing review/publication state on repeated sightings;
- never delete prior facts because a scan failed or an event disappears from one index response;
- never publish automatically.

The workflow prints only aggregate review counts and safe source-health fields. It does not upload raw HTML or the collector report as an artifact.

On 2026-10-07 the first persistence-backed run stopped before contacting the publisher because the collector still attempted to re-read `feeds` through the intentionally restricted public Data API. The workflow now passes the already-verified source snapshot directly to the collector, preserving the fail-closed approval check without reopening public table grants.


## Zero-event diagnostics

The collector report includes only aggregate parser-stage counts: same-host product links, distinct candidate URLs, records formed, records with titles, records with dates, and records with times. These counts distinguish an empty index from candidates that fail card, title, or date/time extraction. The report does not retain response HTML, card text, descriptions, images, or cookies.

## Candidate diagnostics (Issue #87)

Every discovered candidate now appears in the Actions summary and the
`luzzati-candidate-diagnostics` artifact (JSON plus Markdown, retained seven
days). The JSON records index-only vs detail-fetched coverage, HTTP status,
redirect host, explicit year/date text, local time, normalized timestamp,
precision, location/category, extraction methods, and unresolved reasons.
Date snippets contain only the matched date, never descriptions or full HTML.
Yearless dates remain null timestamps; partial facts are diagnostic only and
are not yet separate database columns. `visible_page_fallback` explicitly
flags extraction outside the selected event scope for manual verification.

The existing fail-closed behavior is preserved: robots denial or a failed
detail request stops the run, preserves available diagnostics, and prevents
persistence. Selected but unrequested candidates say `stopped_after_failure`;
candidates outside the cap say `not_fetched_cap`. No recurrence or publication
is enabled. The count inspection also reports URLs that have both undated and
dated facts, without changing or merging them. One URL can have multiple
valid occurrences. Reconciliation remains separate work.

The full-detail experiment (run `37771193165`) already opened all 12 candidates
in 14 requests. It produced five complete timestamps, all historical as of
2026-10-08, seven yearless dates (three also without a recognized time), and
seven locations from visible-page fallback. A known 6 October listing
normalized to 18:00 `Europe/Rome`. Do not repeat the live crawl only to
reproduce these counts; improve year-context resolution and make fallback
provenance explicit in the offline-tested parser instead.

After checks and merge, use **Run manual Giardini Luzzati pilot** on `main`
with `detail_page_limit=12` for the bounded full-detail experiment. Its existing
hosted schema/source preflight still runs before any source request. Review
the artifact and possible stale variants before considering publication or
a second-source comparison. A successful HTTP response or passing offline
test alone does not establish live extraction accuracy.

## Occurrence reconciliation (#93)

Apply the reviewed supersession migration before using the updated importer.
The workflow preflight checks the trusted import function before source contact.
The migration reconciles existing pending undated/dated pairs only when the
source URL has exactly one known occurrence and the titles match. It retains
both row IDs, original source UIDs, evidence, first/last-seen timestamps and
review state; `superseded_by` and `superseded_at` explain the link.

Subsequent imports use the same rule only for a single dated report occurrence.
Shared-URL series, mismatched titles and already-reviewed placeholders remain
for human reconciliation. Partial/index-only scans do not recreate undated rows
when a known occurrence exists. Collector refreshes never overwrite validated,
published or rejected records. The admin queue excludes linked audit rows; an
admin can still inspect them through the private table. Browser users cannot
forge supersession links or change imported identity. No records are deleted
and no publication or recurring collection is enabled by this change.
