# Genova Community Calendar: project scope and launch criteria

## Goal

Create a Genova-first event discovery calendar as a public feature of Porto Aperto | Genova, saving people from checking many local websites. Collect public listings from publishers, institutions, venues, and event platforms; organize and deduplicate them; and offer a compact calendar that updates automatically in Google Calendar, Apple Calendar, and other iCalendar-compatible apps.

This document is the project's guiding definition of success. Implement it in small issues and pull requests. Adapt the existing Community Calendar pipeline where it already meets a requirement rather than rebuilding it. Preserve upstream attribution and the Apache 2.0 license.

The public calendar is free and does not require an account. The source discovery and approval tools are for the maintainer only.

## Porto Aperto | Genova fit

The calendar is the public event-discovery layer of Porto Aperto | Genova: an easy, mobile-first way for people to find activities and connect with the original organizers.

- Keep the public event page and read-only category subscriptions free to use and usable without a personal account.
- Link each listing to its publisher or organizer. Keep the calendar complementary to Porto Aperto's existing community channels: WhatsApp remains the clubhouse and Instagram remains a public discovery channel.
- Use a dedicated Genova event agent that the maintainer can wake remotely. The agent follows version-controlled `AGENT.md` instructions for Genova and nearby Liguria boundaries, enjoyable public events, exclusions, source/access rules, categories, output fields, confidence handling, and cost limits. Discovery suggestions are not permission to collect: only sources explicitly approved and active in the admin directory may be scanned.
- Prefer free-tier hosting and collection methods. Do not enable paid API keys or services until the expected cost and owner are recorded.
- Make the standalone calendar URL easy to share through Porto Aperto's public channels (currently Instagram and WhatsApp). A separate Porto Aperto website is not a launch dependency; add a site link later if one exists.
- Keep source discovery, source approval, collection status, and source troubleshooting in an admin-only area. Public users see the event calendar and filters, not source-management controls.
- Treat “find everything online” as the ambition, not a completeness guarantee: discovery is limited to public/indexable content and supported collection methods. Do not bypass login walls or publisher access rules.

## Intended experience

1. I open the Porto Aperto | Genova page and browse a real calendar, with events grouped by date and links to their original publishers.
2. I can select event categories with checkboxes. A crowded date shows a few compact listings and “+N more”; opening it reveals the full day's events.
3. I subscribe to only the categories I want in Google Calendar, Apple Calendar, or another iCalendar app.
4. As maintainer, I can remotely wake the Genova agent, review its source suggestions, approve which sources can be scanned, and inspect run results and source health.
5. Before approving a UI or data change, I open the working preview on my phone and inspect it.

## Scope

### City and sources

- Start with Genova, using `Europe/Rome` dates and times.
- Define a configurable geographic boundary so nearby Ligurian events can be intentionally included or excluded.
- The dedicated agent reads `AGENT.md` and may search public/indexable web results, links from known local sources, and relevant event directories for enjoyable Genova-area events and candidate publishers, venues, organizers, and platforms. Do not prioritize government meetings. Discovery is best-effort and does not promise exhaustive coverage.
- Audit Visitgenoa, Comune di Genova, Mentelocale Genova, Palazzo Ducale, theater and museum calendars, and relevant event platforms and organizers. These are candidates, not promises of compatible access.
- Require maintainer approval before any discovered source is scanned. Scan only sources marked approved and active in the source directory.
- Record each source's name, URL, collection method, approval/active status, discovery rationale, last successful scan, event count, last error, and access notes. Allow the maintainer to approve, reject, pause, or remove a source.
- Prefer an official ICS feed or API when available, then structured public event pages. Write a source-specific scraper where necessary. Include non-ICS sources.
- Preserve the publisher's name and a link to the original event page. Respect site access rules and rate limits; do not rely on login-protected or social-media scraping.

### Event quality and discovery

- Normalize title, start/end, timezone, venue/address, description, categories/tags, price or free-entry status if published, booking link, canonical event URL, and source metadata. Omit unknown facts rather than inventing them.
- Deduplicate the same event across publishers while retaining source attribution. Preserve separate performances and showtimes.
- Handle edits and cancellations. Flag uncertain or incomplete dates for review instead of publishing misleading times.
- Use AI to suggest one or more categories and a confidence level. Allow the maintainer to correct categories and review uncertain dates, locations, duplicates, and category assignments.
- Support music, theater/performance, art/exhibitions, sports, food/drink, festivals/markets, talks/workshops, family, outdoor/tours, and community/social. “Date night” is an additional tag that can coexist with categories.
- Present events in a date-based calendar. Use category checkboxes for public filtering, show a compact set of event titles in dense date boxes, and expand the selected date to reveal every listing. Show original links clearly.

### Calendar output and volume

- Publish read-only, category-specific ICS subscription URLs with stable event IDs.
- Refresh collected data at least daily once the Genova pipeline is configured. Calendar applications control when they poll a subscribed feed, so display updates may lag publication.
- Use a configurable upcoming-event window, initially 60 days.
- Exclude ordinary opening hours and generic season announcements. Represent a continuous exhibition as one multi-day event rather than one entry per day.
- Let users subscribe to selected categories instead of forcing the entire raw catalog into one calendar.

### Maintenance and review

- Provide an admin-only source dashboard for candidate discovery, approvals, scan status, failures, and category corrections. It must provide an authorized remote wake-up for a manual agent run and show run history. Server-side authorization must protect admin actions; the public page remains usable without an account. Do not enable recurring runs until cost and reliability are reviewed.
- Show failed and stale approved sources, and allow them to be paused or disabled.
- Document how to add and validate a source.
- Keep a clearly labeled sample-data preview that uses no real user sessions or service keys. PR #4 merged the month-grid sample preview. Switch GitHub Pages from the feature branch to `main` / `/(root)` so future updates on the default branch appear. The final phone/laptop review is tracked in Issue #6. GitHub Pages provides one published site, not a unique URL for every pull request.
- Each pull request that changes visible output must include the preview URL and concise review steps. The preview must work on a phone before merge.
- Document the production URL and the path from approved pull request to production.
- Do not expose service keys or enable the fork's scheduled upstream city jobs before configuring Genova's sources, backend, and expected operating costs.

## Suggested implementation order

1. **Fork setup and preview:** Audit dependencies and costs, and provide a working Genova sample preview.
2. **Calendar browsing:** Deliver the mobile-friendly month calendar, category checkboxes, and expandable dense dates with sample data.
3. **Source pilot:** Connect a small varied set of real Genova sources, including a non-ICS source, through the existing normalization pipeline.
4. **Remote Genova agent and admin source directory:** Add the versioned `AGENT.md` criteria, authorized manual wake-up, AI-assisted source candidates, explicit approval, and scan-health controls.
5. **Quality and subscriptions:** Verify deduplication, timezone handling, location filtering, volume limits, category ICS feeds, event changes, scheduled refresh, and maintainer instructions.

## Acceptance criteria for the first usable release

- [ ] The calendar is visibly presented as a Porto Aperto | Genova feature and can be shared through its public channels; browsing and category subscriptions are free and do not require an account.
- [ ] A review preview uses clearly labeled sample data and does not depend on the upstream Supabase project, real user sessions, or service keys.
- [ ] No paid third-party API is needed to view the sample preview; document expected service costs before enabling paid collection features.
- [ ] The sample preview is accessible on mobile; visible-output pull requests include the working preview URL and review steps before merge.
- [ ] The calendar displays a month grid on wide screens and readable date cards on phones; dense dates show “+N more” and expand to all events for that date.
- [ ] Category checkboxes filter one or more categories, including events that carry multiple categories.
- [ ] `Europe/Rome` is applied consistently, including daylight-saving transitions, with no invented start times.
- [ ] At least five independent Genova-area sources work across official/tourism listings, a local publisher, and a direct venue or organizer. At least one working source uses a non-ICS collection method. Any substitutions and their reasons are documented.
- [ ] Every published event has a source name and a working link to the original event listing.
- [ ] The listing can be filtered by date and the requested categories, including a “date night” tag.
- [ ] A dedicated agent can be remotely woken by the maintainer, reads the versioned `AGENT.md` search and output criteria, and reports each run.
- [ ] Admin-only AI source discovery suggests public sources for review; only explicitly approved, active sources are collected, and candidate/scan failures are visible to the maintainer.
- [ ] Duplicate publisher listings display as one event with attribution preserved; separate showtimes stay separate.
- [ ] Multi-day exhibitions do not create a separate all-day entry for each day. Ordinary opening hours and generic season pages do not flood the calendar.
- [ ] Valid category ICS feeds can be subscribed to in Google Calendar and Apple Calendar. Stable IDs allow an edited event to update without creating a duplicate.
- [ ] Updates and cancellations from sources reach the published feed after collection, subject to the calendar client's polling schedule.
- [ ] Collection runs at least daily once enabled, and failed or stale sources are visible to the maintainer without silently erasing valid events from other sources.
- [ ] The repository documents setup, preview, source addition, validation, ongoing costs, and review/release steps.

## Outside the first release

Ticket purchasing, RSVP management, personal accounts, personalized AI scoring, login-protected or comprehensive social-media ingestion, member link/flyer submissions with review, AI-assisted flyer extraction, and expansion to other cities.

## References

- Upstream project: https://github.com/judell/community-calendar
- Candidate Genova sources:
  - https://www.visitgenoa.it/it/eventi
  - https://www.comune.genova.it/vivere-il-comune/eventi
  - https://www.mentelocale.it/genova/eventi/
  - https://palazzoducale.genova.it/eventi/
