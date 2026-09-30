# Genova fork readiness audit

**Reviewed:** 2026-09-30  
**Repository:** [YourMagicGenie/genova-community-calendar](https://github.com/YourMagicGenie/genova-community-calendar)  
**Project tracker:** [Issue #1](https://github.com/YourMagicGenie/genova-community-calendar/issues/1)

This audit completes the repository and operating-cost review at the start of Issue #1. It describes the current fork, not a production launch.

## What is in the fork now

| Area | Current state | What that means for Genova |
| --- | --- | --- |
| License and ownership | Public fork of [judell/community-calendar](https://github.com/judell/community-calendar), carrying the Apache 2.0 license. | Keep upstream attribution and license notices; the fork is a good existing pipeline to adapt. |
| Dependencies | The data pipeline uses Python 3.10+ and `requirements.txt`; the development file adds pytest. Several packages are pinned to older versions, while `icalendar`, `recurring-ical-events`, and `anthropic` use open-ended lower bounds. The UI loads Supabase JS v2 and rrule 2.8.1 from jsDelivr; there is no root `package.json`. | Keep the existing stack for the sample preview. Review dependency freshness and reproducibility before production, rather than doing a broad upgrade in the first preview slice. |
| Frontend | XMLUI app under `xmlui/`. Event rows are pushed into the UI by `xmlui/shell.js`; `xmlui/Main.xmlui` displays and filters them. | Preserve the existing UI and give its event loader a safe sample-data mode for review. |
| Backend | `xmlui/config.json` still points at the upstream Supabase project. No separate Genova backend is configured. | Do not load or write Genova events through that configuration. Create a separate backend only when the real-source vertical slice is ready. |
| City scope | The inherited source has eight US/Canada city folders and no Genova entry. | Do not activate the inherited all-city job. Configure one Genova city before collection. |
| Collection jobs | `.github/workflows/generate-calendar.yml` has a nightly schedule and manual dispatch. With no `ENABLED_CITIES` variable, its default is every `cities/*/feeds.txt` folder. The job has write permission and reads Supabase service-key and optional Anthropic/Ticketmaster API variables/secrets. | Keep collection disabled until the Genova source set, backend, scope, and any API spend are approved. Never reuse an upstream service key. |
| Pull request checks | `.github/workflows/validate-pr.yml` runs Python tests, local Supabase database tests, and a Node performance check. `regression-tests.yml` is manual and expects remote test secrets. No Actions runs are visible yet in the fork. | Public-repository standard GitHub-hosted runners are currently free. Keep PR checks free of production credentials; do not interpret the absence of runs as a successful test. |
| Hosting and preview | GitHub Pages is now publishing the sample-preview branch; the owner confirmed the preview works on a phone. The local `.bram.json` example starts a local server for Bloomington. | Keep sample data on the preview branch. After its page changes merge, switch Pages to `main` / root so future main-branch updates publish. Pages is a single site, not a unique preview deployment for every PR. |
| Repository size | GitHub reports roughly 465 MB for the fork. | Avoid adding generated event archives or large preview assets; include repo checkout/build time in the first preview-host smoke test. |

## Operating cost and preview choice

- **Preview:** GitHub Pages is already publishing the sample-preview branch with fictional data and no Supabase calls. After merging the page PR, select `main` and `/(root)` in Settings → Pages so the same site follows main-branch updates. Pages does not make a separate URL per PR; if unique automatic PR previews become important later, Cloudflare Pages is an optional alternative.
- **GitHub Actions:** standard GitHub-hosted runners are free for public repositories. The inherited collection workflow may still call separately billed services if API keys are configured; that is a different cost from GitHub Actions.
- **Supabase:** the UI points to the upstream project's public configuration today. Supabase documents that Free Plan projects with low activity over seven days can be paused. A separate Genova project and an uptime plan are needed before real public events depend on it.
- **AI and ticketing APIs:** the workflow has optional Anthropic and Ticketmaster credentials. Do not configure either for the sample preview. Check current terms, quotas, and possible charges before enabling either for collection.

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
