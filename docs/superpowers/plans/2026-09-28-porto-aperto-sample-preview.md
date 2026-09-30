# Genova Calendar Preview: Current Design and Review Guide

> **Status:** This note supersedes the original preview implementation plan. The original plan expected to route the sample through the upstream XMLUI/Supabase app and use Cloudflare Pages. The current preview is a separate static page with local fictional data, and the owner chose GitHub Pages.

## What the preview demonstrates

The route `/?city=genova&preview=sample` opens the Porto Aperto | Genova page. It is intentionally separate from the inherited app and makes no calls to the upstream Supabase project.

The updated preview shows a month calendar. It has category checkboxes, a Date night filter, month navigation, and a compact view of each date. A crowded day shows three event names and a “+N more” control that expands the rest. Its fixture has 16 fictional listings on one day so the expanded view can be checked. Every sample link uses `example.org`, and the page is labeled as sample content.

## Hosting and review

- GitHub Pages currently publishes the `issue-1/genova-sample-preview` branch from the repository root. The owner confirmed the page works on a phone.
- Preview URL: <https://yourmagicgenie.github.io/genova-community-calendar/?city=genova&preview=sample>
- After PR #4 is merged, set **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/(root)`**. That keeps the same page publishing from the default branch as later changes merge.
- This setup provides one published site. It does not create a unique deployment for every pull request. The current owner-managed preview branch is sufficient for this first page review.

## Current implementation and verification

- The page, fixture, and dependency-free behavior tests are in [PR #4](https://github.com/YourMagicGenie/genova-community-calendar/pull/4).
- Run the focused tests with `node --test tests/sample-preview.test.js`.
- The sample fixture must fail closed on load or validation errors. It must never fall back to inherited event data.
- No real event sources, automated collection schedule, admin tools, service keys, or production backend are enabled by the preview.
- Browser-level phone review remains the owner-facing check; automated DOM tests do not replace checking the page on the actual phone.

## Next tracked work

- [Issue #6](https://github.com/YourMagicGenie/genova-community-calendar/issues/6): calendar grid, date expansion, and category filters.
- [Issue #5](https://github.com/YourMagicGenie/genova-community-calendar/issues/5): admin-only AI source discovery and approved-source management.
- [Issue #1](https://github.com/YourMagicGenie/genova-community-calendar/issues/1) remains the overall launch tracker.