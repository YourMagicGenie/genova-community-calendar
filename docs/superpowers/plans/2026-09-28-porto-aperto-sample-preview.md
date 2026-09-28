# Porto Aperto | Genova Sample Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every event-discovery pull request a mobile-friendly preview of the existing calendar UI using sample Genova events, with no production backend access.

**Architecture:** Keep the existing XMLUI interface and production event pipeline. Add an explicit `?city=genova&preview=sample` path that reads a small local fixture and bypasses the Supabase event fetch, cached upstream session, and write controls. Connect the repository to Cloudflare Pages after that path passes its smoke test so each pull request receives its own public preview URL.

**Tech Stack:** Existing XMLUI, HTML, JavaScript, JSON, Python `http.server` for local preview, dependency-free Node.js tests, and Cloudflare Pages Git integration.

**Spec:** [`PROJECT_SCOPE.md`](../../../PROJECT_SCOPE.md)

## Global Constraints

- Start with Genova, using `Europe/Rome` dates and times.
- Use a configurable upcoming-event window, initially 60 days.
- Preserve the publisher's name and a link to the original event page.
- Refresh collected data at least daily once the Genova pipeline is configured.
- Do not expose service keys or enable the fork's scheduled upstream city jobs before configuring Genova's sources, backend, and expected operating costs.
- Ticket purchasing, RSVP management, personal accounts, personalized AI scoring, comprehensive social-media ingestion, member link/flyer submissions with review, AI-assisted flyer extraction, and expansion to other cities are outside the first release.

## Review Focus

- No `preview=sample` parameter: the current production event fetch and app behavior remain unchanged.
- A browser with an old upstream Supabase login saved locally opens sample mode: no Supabase REST, auth, or user-specific requests are made.
- The sample fixture is missing or invalid: the preview shows a clear error and never falls back to upstream data.
- Sample dates cross a Genova weekend or daylight-saving boundary: displayed times remain correct in `Europe/Rome`.
- A sample event has no price or end time: the preview leaves those facts unknown instead of inventing them.

---

## File Structure

- `xmlui/sample-events.json` — small, explicitly fictional fixture with representative categories, dates, source labels, and source links.
- `xmlui/sample-preview.js` — testable, dependency-free sample-mode detection and fixture loader.
- `xmlui/index.html` — load preview-mode detection before the main shell.
- `xmlui/shell.js` — route the existing pushed event stream to the fixture in sample mode; bypass event caching and network reads on that route.
- `xmlui/Main.xmlui` — disable Supabase-backed user, enrichment, and edit controls while in sample mode; display a visible sample-preview label.
- `tests/sample-preview.test.js` — Node built-in tests for opt-in behavior, fixture validation, and fail-closed loading.
- `docs/app-architecture.md` and `CONTRIBUTING.md` — local preview command, sample URL, and how to find/review the Cloudflare PR preview.

## Tasks

### Task 1: Add an isolated sample-event provider

- [ ] Write `tests/sample-preview.test.js` first using Node's built-in `node:test` and a mocked browser `window`/fetch.
- [ ] Run `node --test tests/sample-preview.test.js`; confirm the new sample-mode behavior fails before implementation.
- [ ] Add `xmlui/sample-events.json` with clearly fictional, varied Genova-style listings. Include source name/link, category, date/time, and venue; do not use private event data or present examples as real listings.
- [ ] Add `xmlui/sample-preview.js` with only the small provider helpers needed to parse `preview=sample` and load/validate the fixture.
- [ ] Re-run `node --test tests/sample-preview.test.js`; verify sample mode loads the fixture, normal mode does not request it, and a failed fixture request returns a visible error without fallback.
- [ ] Add an explicit Node setup and this test command to the PR check workflow, then run the check.

### Task 2: Connect the provider to the existing UI safely

- [ ] Add the opt-in sample route to `xmlui/index.html` and route events in `xmlui/shell.js` through the sample provider when enabled.
- [ ] In `xmlui/Main.xmlui`, suppress event enrichments, restored auth state, personal data sources, and write/edit controls in sample mode; add an always-visible “Sample events” label.
- [ ] Extend the browser test to intercept network requests for `https://*.supabase.co` while opening `?city=genova&preview=sample`; assert no request escapes and the rendered fixture cards show their source links and category tags.
- [ ] Serve the app with `python3 -m http.server 8080` and review the sample URL at a phone-sized viewport.
- [ ] Run the existing Python suite with `make test` and the existing XMLUI browser test page. Record which checks ran; do not describe unrun GitHub checks as green.

### Task 3: Enable reviewable pull-request previews

- [ ] Connect `YourMagicGenie/genova-community-calendar` to a Cloudflare Pages project through its GitHub integration. Use the static sample preview only; add no service keys or Functions.
- [ ] Set `main` as the production branch for the separate calendar preview URL. Do not attach a Porto Aperto custom domain during this test.
- [ ] Open a test pull request and verify Cloudflare attaches a unique preview URL, updates it after a new commit, and that it opens on a phone without a login.
- [ ] Document the preview link location, review steps, and owner-managed connection in `CONTRIBUTING.md`.
- [ ] Share the verified calendar URL through Porto Aperto's public Instagram profile or other existing community channels. This is an owner update; a separate website repository is not required.

## Completion Check

The preview slice is ready when sample mode is isolated from the upstream backend, automated checks and the phone-sized UI review pass, and a sample-only Cloudflare preview URL is visible from a pull request. The overall Issue #1 remains open until the real-source, calendar-feed, and operations criteria in `PROJECT_SCOPE.md` pass.
