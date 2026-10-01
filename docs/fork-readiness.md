# Genova fork readiness audit

**Reviewed:** 2026-09-30; collection workflow status updated 2026-10-01
**Repository:** [YourMagicGenie/genova-community-calendar](https://github.com/YourMagicGenie/genova-community-calendar)  
**Project tracker:** [Issue #1](https://github.com/YourMagicGenie/genova-community-calendar/issues/1)

This audit completes the repository and operating-cost review at the start of Issue #1. It describes the current fork, not a production launch.

## What is in the fork now

| Area | Current state | What that means for Genova |
| --- | --- | --- |
| License and ownership | Public fork of [judell/community-calendar](https://github.com/judell/community-calendar), carrying the Apache 2.0 license. | Keep upstream attribution and license notices; the fork is a good existing pipeline to adapt. |
| Dependencies | The inherited pipeline and local pipeline tests use Python 3.12. Direct production and test dependencies are exactly pinned in `requirements.txt` and `requirements-dev.txt`; Dependabot proposes weekly Python and GitHub Actions updates, and the PR workflow runs `pip-audit` against pinned dependencies. The UI loads Supabase JS v2 and rrule 2.8.1 from jsDelivr; there is no root `package.json`. | Keep the existing stack for the sample preview. Review dependency freshness and reproducibility before production, rather than doing a broad upgrade in the first preview slice. |
| Frontend | The public root and `/xmlui/` entry route to the isolated sample preview. Other city requests show an unconfigured message. The inherited XMLUI app files remain in the repository but are not loaded by these public routes. | Public browsing currently shows only fictional Genova fixtures and an explicit no-live-feed status. |
| Backend | The upstream Supabase URL and publishable key were removed from `xmlui/config.json`; no Genova backend is configured. | Do not add backend credentials until the owner chooses and verifies a fork-owned project. The public entry points do not load the inherited database client. |
| City scope | `cities.json` now lists only Genova in `Europe/Rome`; inherited city folders remain as reference code. The public source-priority list is empty until sources are approved. | Do not activate inherited cities or publishers. Add Genova sources only after owner approval and access review. |
| Collection jobs | The inherited nightly, write-enabled multi-city publisher was retired in issue #10. `.github/workflows/generate-calendar.yml` is now a manual, read-only Genova scope check with no schedule, secrets, source scans, or writes. The owner has kept that workflow disabled in Actions. | A local dry run requires an explicit `genova` scope; actual collection still needs approved sources, a fork-owned backend, access controls, and cost/recovery review. See [Genova collection safety](genova-collection-safety.md). |
| Pull request checks | `.github/workflows/validate-pr.yml` uses Python 3.12, audits dependencies, runs Python and feed checks, local Supabase database tests, a Node performance check, and a Markdown link check. The fork's Actions were enabled and PR #9's three jobs passed; `regression-tests.yml` remains manual. | Keep PR checks free of production credentials and require real passing results before merging. |
| Hosting and preview | The GitHub Pages URL serves the Genova sample preview. The repository has no Bram integration; run the local preview with the command in the root README. | Pages publishes one site, not a separate preview for every PR. The remaining phone/laptop interaction review is tracked in issue #6. |
| Repository size | GitHub reports roughly 465 MB for the fork. | Avoid adding generated event archives or large preview assets; include repo checkout/build time in the first preview-host smoke test. |

## Operating cost and preview choice

- **Preview:** GitHub Pages is publishing fictional data with no backend configuration or live Genova feed. Verify that Settings → Pages publishes `main` and `/(root)` so merged updates reach the same site. Pages does not make a separate URL per PR; if unique automatic PR previews become important later, Cloudflare Pages is an optional alternative.
- **GitHub Actions:** standard GitHub-hosted runners are free for public repositories. The replacement collection dry run makes no external service calls. Any future live collector needs a fresh cost and quota review.
- **Supabase:** no project is configured for the public Genova page. A fork-owned backend and an uptime plan are needed before real public events depend on it.
- **AI and ticketing APIs:** the current dry run has no Anthropic or Ticketmaster credentials. Check current terms, quotas, and possible charges before adding either to a future collector.

Provider limits can change; this audit was checked on 2026-09-28.

## Recommended order

1. Add a clearly labeled fixture-backed preview to the existing UI. It must fail closed if its fixture cannot load and make no calls to Supabase, including when the browser has an old upstream login session.
2. The owner connected GitHub Pages to the sample-preview branch and confirmed that the preview works on a phone. After the page PR is merged, change the publishing branch to `main` / `/(root)` so later updates publish from the default branch.
3. Once a standalone calendar URL exists, share it through Porto Aperto's public channels. No separate website repository is needed; a site link can be added later if one exists.
4. After the preview works, create a separate Genova Supabase project (or choose a different backend) and configure a Genova-only collection pipeline. Store any service key in GitHub Actions secrets, never in a file or chat.
5. Review the source list, geographic boundary, categories, and event examples with a Porto Aperto community curator before the real-source pilot.

## Owner actions later (you can do these without another contributor)

- [ ] Decide which Porto Aperto public channels should point to the calendar once its public URL exists.
- [x] Connect GitHub Pages to the sample-preview branch and verify the page on a phone. After the calendar page PR is merged, switch Pages to `main` / `/(root)`.
- [ ] Before real events are published, a project owner chooses and configures a separate Genova backend and records the expected ongoing cost.
- [ ] Review the Genova boundary, candidate sources, category examples, and weekly review process yourself; community input can be added when useful.

There is no local programming task needed to review this sample page. Real event collection will later need an isolated Genova backend and a protected admin service before live sources are scanned.

## References

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Pages publishing sources](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Cloudflare Pages GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
- [Supabase Free Plan project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
