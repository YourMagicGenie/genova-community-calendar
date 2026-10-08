# Genova fork readiness audit

**Reviewed:** 2026-10-05; Supabase schema applied, security review in progress
**Repository:** [YourMagicGenie/genova-community-calendar](https://github.com/YourMagicGenie/genova-community-calendar)  
**Project tracker:** [Issue #1](https://github.com/YourMagicGenie/genova-community-calendar/issues/1)

This audit completes the repository and operating-cost review at the start of Issue #1. It describes the current fork, not a production launch.

## What is in the fork now

| Area | Current state | What that means for Genova |
| --- | --- | --- |
| License and ownership | Public fork of [judell/community-calendar](https://github.com/judell/community-calendar), carrying the Apache 2.0 license. | Keep upstream attribution and license notices; the fork is a good existing pipeline to adapt. |
| Dependencies | The inherited pipeline and local pipeline tests use Python 3.12. Direct production and test dependencies are exactly pinned in `requirements.txt` and `requirements-dev.txt`; Dependabot proposes weekly Python and GitHub Actions updates, and the PR workflow runs `pip-audit` against pinned dependencies. The UI loads Supabase JS v2 and rrule 2.8.1 from jsDelivr; there is no root `package.json`. | Keep the existing stack for the sample preview. Review dependency freshness and reproducibility before production, rather than doing a broad upgrade in the first preview slice. |
| Frontend | The public root and `/xmlui/` entry route to the Genova sample preview. Other city requests show an unconfigured message. The preview now reads only the field-limited fictional demo RPC; reviewed real events remain on a separate route. | Public browsing stays clearly labeled fictional until real events are explicitly reviewed and published. |
| Backend | `xmlui/config.json` contains the owner-controlled Genova Supabase URL and publishable key. The sample page reads fictional records through a public RPC; the admin page uses Supabase Auth plus the private `admin_users` allowlist for review, edits, and demo reset. Browser code contains no service-role key. | Keep collected facts and audit history private with RLS. Keep the demo set isolated from collected, submitted, and published event rows. |
| City scope | `cities.json` now lists only Genova in `Europe/Rome`; inherited city folders remain as reference code. The public source-priority list is empty until sources are approved. | Do not activate inherited cities or publishers. Add Genova sources only after owner approval and access review. |
| Collection jobs | The inherited nightly, write-enabled multi-city publisher was retired in issue #10. `.github/workflows/generate-calendar.yml` is now a manual, read-only Genova scope check with no schedule, secrets, source scans, or writes. The owner has kept that workflow disabled in Actions. | A local dry run requires an explicit `genova` scope; actual collection still needs approved sources, a fork-owned backend, access controls, and cost/recovery review. See [Genova collection safety](genova-collection-safety.md). |
| Pull request checks | `.github/workflows/validate-pr.yml` uses Python 3.12, audits dependencies, runs Python and feed checks, local Supabase database tests, a Node performance check, a Markdown link check, and the browser smoke test. The fork's Actions were enabled and PR #9's three jobs passed; `regression-tests.yml` remains manual. | Keep PR checks free of production credentials and require real passing results before merging. |
| Hosting and preview | The GitHub Pages URL serves the Genova sample preview. The repository has no Bram integration; run the local preview with the command in the root README. | Pages publishes one site, not a separate preview for every PR. The remaining phone/laptop interaction review is tracked in issue #6. |
| Repository size | GitHub reports roughly 465 MB for the fork. | Avoid adding generated event archives or large preview assets; include repo checkout/build time in the first preview-host smoke test. |

## Operating cost and preview choice

- **Preview:** GitHub Pages publishes the clearly labeled fictional demo set from a field-limited public RPC in the owner Supabase project, so an admin's demo reset is reflected on the sample calendar. This uses only the publishable key and no visitor session. The reviewed live-event route remains separate. Verify that Settings → Pages publishes `main` and `/(root)` so merged updates reach the same site. Pages does not make a separate URL per PR; if unique automatic PR previews become important later, Cloudflare Pages is an optional alternative.
- **GitHub Actions:** standard GitHub-hosted runners are free for public repositories. The replacement collection dry run makes no external service calls. Any future live collector needs a fresh cost and quota review.
- **Supabase:** a free-plan owner project is connected. Public demo reads use a narrowly scoped function; admin edits, approvals, audit history, and demo reset require an already approved Auth identity. No service-role key is exposed to the browser.
- **AI and ticketing APIs:** the current dry run has no Anthropic or Ticketmaster credentials. Check current terms, quotas, and possible charges before adding either to a future collector.

Provider limits can change; this audit was checked on 2026-09-28.

## Recommended order

1. The first review slice used local fictional fixtures without Supabase. Issue #86 now moves the demo set to a separate, clearly fictional table so the owner can remove or restore it from the website's admin page; only the public demo RPC is available to unauthenticated visitors.
2. The owner connected GitHub Pages to the sample-preview branch and confirmed that the preview works on a phone. After the page PR is merged, change the publishing branch to `main` / `/(root)` so later updates publish from the default branch.
3. Once a standalone calendar URL exists, share it through Porto Aperto's public channels. No separate website repository is needed; a site link can be added later if one exists.
4. After the preview works, use the owner-controlled Genova Supabase project for the admin-only collection pipeline. Keep Supabase secret keys in Edge Function secrets, never in GitHub Actions, a file, or chat.
5. Review the source list, geographic boundary, categories, and event examples with a Porto Aperto community curator before the real-source pilot.

## Owner actions later (you can do these without another contributor)

- [ ] Decide which Porto Aperto public channels should point to the calendar once its public URL exists.
- [x] Connect GitHub Pages to the sample-preview branch and verify the page on a phone. After the calendar page PR is merged, switch Pages to `main` / `/(root)`.
- [x] Choose the owner-controlled Genova Supabase project and connect its public URL/key in the inherited client config. The schema is applied. Complete Issue #59, then set up the Auth user and Edge Function secrets before the fixture run.
- [ ] Review the Genova boundary, candidate sources, category examples, and weekly review process yourself; community input can be added when useful.

There is no local programming task needed to review this sample page. Real event collection will later need an isolated Genova backend and a protected admin service before live sources are scanned.

## References

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub Pages publishing sources](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Cloudflare Pages GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
- [Supabase Free Plan project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
