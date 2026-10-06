# Manual Giardini Luzzati pilot run

The first real-source import remains manual. The workflow **Run manual Giardini Luzzati pilot** has no schedule and uses the same `genova-supabase-bootstrap` environment already used for reviewed migrations.

Before it contacts the publisher, it verifies that migration `20261006124729_genova_first_source_persistence.sql` is present in hosted migration history. The collector then performs its bounded robots/index request, validates the facts-only report, and persists the result transactionally.

Persistence rules:

- append one private scan-provenance row;
- upsert occurrences by stable `source_uid`;
- refresh facts and `last_seen` only when the stored source ID and normalized URL still match;
- preserve the existing review/publication state on repeated sightings;
- never delete prior facts because a scan failed or an event disappears from one index response;
- never publish automatically.

The workflow prints only aggregate review counts and safe source-health fields. It does not upload raw HTML or the collector report as an artifact.

For the 2026-10-06 pilot, do not run this workflow again: Issue #50 already used the source's request budget for that day. The first manual persistence run should occur on a later day after the hosted migration is applied.
