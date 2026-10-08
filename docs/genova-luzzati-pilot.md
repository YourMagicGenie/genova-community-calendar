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
