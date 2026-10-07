# Changelog

- 2026-10-02 — Connected the inherited client configuration to the owner-controlled Genova Supabase project while keeping the public calendar on clearly labeled fictional fixtures; no live events or collection are enabled ([issue #11](https://github.com/YourMagicGenie/genova-community-calendar/issues/11)).
- 2026-10-02 — Restricted the dashboard-created automatic-RLS helper from public API roles and verified that its event trigger still enables RLS on new public tables ([issue #41](https://github.com/YourMagicGenie/genova-community-calendar/issues/41)).
- 2026-10-02 — Matched the repository migration filename to the version recorded in the owner Supabase project ([issue #43](https://github.com/YourMagicGenie/genova-community-calendar/issues/43)).

This is the short, human-readable record of changes to the Porto Aperto | Genova calendar. [Git history](https://github.com/YourMagicGenie/genova-community-calendar/commits/main/) and pull requests contain the technical details. Entries under **Unreleased** are merged work toward the first usable release; they do not mean a live Genova event collection service exists.

## Unreleased

- 2026-10-07 — Fixed the manual Giardini Luzzati pilot to pass its already-verified active source snapshot from the guarded database check into the collector instead of re-reading `feeds` through the intentionally restricted public Data API (issue #51).

- 2026-10-06 — Prepared a gated, private, admin-reviewed community event submission path and public form; activation awaits hosted migration, live calendar integration, and privacy copy (issue #68).

- 2026-10-06 — Added the first-source persistence/review boundary for Issue #51: Luzzati is registered in the existing feed registry, collected facts and scan provenance are private by default, publication requires an active source plus known start time, and the public route exposes only reviewed facts.

- 2026-10-06 — Added a bounded robots-aware check for the candidate Giardini Luzzati event-index route, reporting only access status and page identity with no retained page copy (issue #50).

- 2026-10-06 — Made the manual Luzzati probe report robots and event HTTP status, allow/disallow decision, request count, and crawl delay on success or skip, with offline regression coverage (issue #50).

- 2026-10-05 — Reframed source collection as an owner-selected whitelist with path-level crawler compliance and facts-and-links records; selected Giardini Luzzati / Spazio Comune and added a manual robots-aware one-event probe that writes no calendar or database data (issue #50).

- 2026-10-05 — Closed anonymous access to inherited event/curator views and the curator-name lookup; preserved signed-in self-identity checks and guarded admin removal, with pgTAP coverage and a guarded `pg_net` schema move (issue #59).

- 2026-10-05 — Fixed migration-workflow preflight and postflight snapshots to use read-only SQL over the IPv4 pooler instead of the Management API query endpoint, which requires `database_write` for this CLI operation (issue #59).

- 2026-10-04 — Added a guarded manual preview/apply path for one later Genova database migration, with remote history and RLS checks (issue #59).

- 2026-10-04 — Restricted inherited privileged refresh and trigger functions from direct public execution and pinned their search paths after the hosted schema bootstrap exposed Security Advisor warnings (issue #59).

- 2026-10-04 — Switched the Supabase bootstrap Security Advisor report to the read-only API, avoiding the CLI's temporary login-role request for Database Read-write (issue #47).

- 2026-10-04 — Listed every scoped token permission for the one-time Supabase bootstrap and made preview verify Security Advisor access before applying schema changes (issue #47).

- 2026-10-04 — Clarified the scoped token permission needed for the bootstrap runner's IPv4 pooler and added an early check before any hosted migration step (issue #47).

- 2026-10-04 — Added explicit static Worker configuration with a Preview block so Cloudflare can build PR previews without changing the fictional Genova calendar or enabling collection (issue #52).

- 2026-10-04 — Added a guarded, one-time Supabase migration preview/apply workflow with remote postflight checks and a Security Advisor report for owner review. This PR does not apply migrations to the hosted project (issue #47).

- 2026-10-04 — Added an admin-only fixture run with a `main`-restricted callback secret, retry and recovery handling, explicit Genova fixture validation, and private run history; it scans zero websites and writes zero public events (issues #5 and #45).

- 2026-10-01 — Added the private database run-history foundation for the future Genova agent, including admin-only reads, server-only writes, instruction revision and result fields, and a single in-flight-run guard. This does not enable sign-in, discovery, collection, or scheduled jobs (issue #5).

- 2026-10-01 — Standardized the inherited pipeline and local test runtime on Python 3.12, pinned direct Python dependencies, added weekly Dependabot updates and a pip-audit check, and added an explicit offline ICS fixture check (issue #19).

- 2026-10-01 — Removed stale build logs and generated Santarosa regression videos from the working tree; manual test recordings are retained as short-lived Actions artifacts, and the inventory explains which inherited feeds/reports remain in use (issue #18).

- 2026-10-01 — Added a headless Chromium smoke test for the Genova sample preview at desktop and phone sizes, covering navigation, category filtering, dense-day expansion, browser errors, and horizontal overflow (issue #16).

- 2026-10-01 — Clarified that a small facts-only pilot may test public event listings with original short summaries and direct source links, while cover-image reuse remains a separate rights check (issue #5).

- 2026-10-01 — Added preliminary rights and reuse findings to the Genova source audit; the candidate pages remain pending and none has confirmed scan permission or a usable feed/API (issue #5).

- 2026-10-01 — Recorded an initial five-source Genova candidate audit with observed coverage, duplication/geography risks, and access checks still required; none is approved or active (issue #5).

- 2026-10-01 — Added the dedicated event-agent operating contract for Genova source discovery, approval boundaries, event fields, categories, confidence, and cost limits; no agent or scanning workflow is enabled yet (issue #5).

- 2026-10-01 — Added private source-review metadata and pending/active/paused/rejected/removed states; public reads expose active sources only, and admin permissions remain enforced by Supabase RLS (issue #13).
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
