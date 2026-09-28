# Genova fork readiness audit

**Reviewed:** 2026-09-28  
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
| Hosting and preview | The GitHub repository currently has Pages disabled. The local `.bram.json` example starts a local server for Bloomington, not a public Genova preview. | A separate, sample-data preview host is still required to satisfy the mobile review criterion. |
| Repository size | GitHub reports roughly 465 MB for the fork. | Avoid adding generated event archives or large preview assets; include repo checkout/build time in the first preview-host smoke test. |

## Operating cost and preview choice

- **Preview recommendation:** connect the repository to Cloudflare Pages using its GitHub integration after sample mode is implemented. Cloudflare documents a unique preview URL for each pull request; preview deployments default to a `noindex` response. Its Free plan currently allows 500 builds per month and one concurrent build. This static preview should use fictional sample events and no Cloudflare Functions or Supabase calls.
- **GitHub Actions:** standard GitHub-hosted runners are free for public repositories. The inherited collection workflow may still call separately billed services if API keys are configured; that is a different cost from GitHub Actions.
- **Supabase:** the UI points to the upstream project's public configuration today. Supabase documents that Free Plan projects with low activity over seven days can be paused. A separate Genova project and an uptime plan are needed before real public events depend on it.
- **AI and ticketing APIs:** the workflow has optional Anthropic and Ticketmaster credentials. Do not configure either for the sample preview. Check current terms, quotas, and possible charges before enabling either for collection.

Provider limits can change; this audit was checked on 2026-09-28.

## Recommended order

1. Add a clearly labeled fixture-backed preview to the existing UI. It must fail closed if its fixture cannot load and make no calls to Supabase, including when the browser has an old upstream login session.
2. Once sample mode is ready, connect the fork to Cloudflare Pages for unique PR preview URLs. This is a one-time account/dashboard action for you as owner; the preview stays separate from Porto Aperto's community channels.
3. Once a standalone calendar URL exists, share it through Porto Aperto's public channels. No separate website repository is needed; a site link can be added later if one exists.
4. After the preview works, create a separate Genova Supabase project (or choose a different backend) and configure a Genova-only collection pipeline. Store any service key in GitHub Actions secrets, never in a file or chat.
5. Review the source list, geographic boundary, categories, and event examples with a Porto Aperto community curator before the real-source pilot.

## Owner actions later (you can do these without another contributor)

- [ ] Decide which Porto Aperto public channels should point to the calendar once its public URL exists.
- [ ] Once sample mode is ready, connect the repository to Cloudflare Pages (or choose another host for unique PR previews). This is a one-time dashboard action; no additional contributor is required.
- [ ] Before real events are published, a project owner chooses and configures a separate Genova backend and records the expected ongoing cost.
- [ ] Review the Genova boundary, candidate sources, category examples, and weekly review process yourself; community input can be added when useful.

There is no local programming task for you right now. Later, you will need the one-time preview-host setup and a separate Genova backend before real events are published.

## References

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Pages custom workflow setup](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Cloudflare Pages GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
- [Cloudflare Pages Free plan limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Supabase Free Plan project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
