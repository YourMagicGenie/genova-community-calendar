# Changelog

This is the short, human-readable record of changes to the Porto Aperto | Genova calendar. [Git history](https://github.com/YourMagicGenie/genova-community-calendar/commits/main/) and pull requests contain the technical details. Entries under **Unreleased** are merged work toward the first usable release; they do not mean a live Genova event collection service exists.

## Unreleased

- 2026-10-01 — Added one Genova category list for the sample filters and event-normalization contract; unknown or uncertain labels remain reviewable, and Date night stays a tag (issue #15).
- 2026-10-01 — Source candidates stay pending until an explicit maintainer approval; collectors only use active database rows and stop safely when approval state is unavailable (issue #13).
- 2026-10-01 — Removed Bloomington-specific Bram settings and tracked machine-local Claude memory; documented the supported Genova preview path ([issue #17](https://github.com/YourMagicGenie/genova-community-calendar/issues/17)).
- 2026-10-01 — Replaced inherited upstream onboarding and source request instructions with Genova-specific preview guidance and source review forms ([issue #14](https://github.com/YourMagicGenie/genova-community-calendar/issues/14)).
- 2026-10-01 — Protected the inherited event writer with a server-only credential, strict Genova payload checks, no upstream repository fallback, and safe handling that skips stale-event cleanup after a failed upload ([issue #12](https://github.com/YourMagicGenie/genova-community-calendar/issues/12)).
- 2026-10-01 — Isolated the public Genova preview from upstream Supabase and inherited cities; live event collection is still unconfigured ([issue #11](https://github.com/YourMagicGenie/genova-community-calendar/issues/11)).
- 2026-10-01 — Retired the inherited all-city daily publisher in favor of a Genova-only manual dry run with no writes or external service calls ([issue #10](https://github.com/YourMagicGenie/genova-community-calendar/issues/10)).
- 2026-10-01 — Fixed the report schema link and added a PR check for broken local Markdown links ([issue #21](https://github.com/YourMagicGenie/genova-community-calendar/issues/21)).
- 2026-10-01 — Started this changelog and added a pull request prompt to keep it current ([issue #22](https://github.com/YourMagicGenie/genova-community-calendar/issues/22)).
- 2026-10-01 — Replaced inherited multi-city agent instructions with Genova-specific guidance; the event-curation agent itself remains future work ([PR #9](https://github.com/YourMagicGenie/genova-community-calendar/pull/9)).
- 2026-09-30 — Clarified the Genova launch scope and admin-only source approval requirements ([PR #7](https://github.com/YourMagicGenie/genova-community-calendar/pull/7)).
- 2026-09-30 — Added a fictional Genova month-calendar preview with filters and crowded-day expansion ([PR #4](https://github.com/YourMagicGenie/genova-community-calendar/pull/4)).
- 2026-09-30 — Documented fork readiness, inherited dependencies, and hosting risks ([PR #2](https://github.com/YourMagicGenie/genova-community-calendar/pull/2)).

When the first release is verified with real sources, move the relevant entries into a dated release section. Each later PR should add a concise line here, or explain in its PR body why no reader or maintainer-facing change warrants one.
