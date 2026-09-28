# Genova fork readiness audit

**Reviewed:** 2026-09-28  
**Repository:** [YourMagicGenie/genova-community-calendar](https://github.com/YourMagicGenie/genova-community-calendar)  
**Project tracker:** [Issue #1](https://github.com/YourMagicGenie/genova-community-calendar/issues/1)

This audit completes the repository and operating-cost review at the start of Issue #1. It describes the current fork, not a production launch.

## What is in the fork now

| Area | Current state | What that means for Genova |
| --- | --- | --- |
| License and ownership | Public fork of [judell/community-calendar](https://github.com/judell/community-calendar), carrying the Apache 2.0 license. | Keep upstream attribution and license notices; the fork is a good existing pipeline to adapt. |
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
2. Have a repository owner or Porto Aperto deployment maintainer connect the fork to Cloudflare Pages for unique PR preview URLs. Use sample data only and keep the production branch's external Porto Aperto domain unconfigured until reviewed.
3. Identify the Porto Aperto website repository and public URL, then add a link to the calendar there. The current GitHub connection exposes only the calendar fork, so this repository is not available to change in this work.
4. After the preview works, create a separate Genova Supabase project (or choose a different backend) and configure a Genova-only collection pipeline. Store any service key in GitHub Actions secrets, never in a file or chat.
5. Review the source list, geographic boundary, categories, and event examples with a Porto Aperto community curator before the real-source pilot.

## Work that needs a human outside this repository

- [ ] A Porto Aperto site/deployment maintainer identifies the current public site URL and repository and decides where a calendar link belongs.
- [ ] Before the first UI pull request that needs a phone preview, a repository owner or the deployment maintainer connects this repository to Cloudflare Pages (or confirms an existing host that provides unique PR preview URLs). This requires a human account/dashboard action.
- [ ] Before real events are published, a project owner chooses and configures a separate Genova backend and records the expected ongoing cost.
- [ ] A local curator reviews the Genova boundary, candidate sources, category examples, and the weekly review process.

You do not need to install anything on your computer for this documentation and audit PR. The first phone-preview URL and any real-event publication do need the external setup above.

## References

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Pages custom workflow setup](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Cloudflare Pages GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
- [Cloudflare Pages Free plan limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Supabase Free Plan project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
