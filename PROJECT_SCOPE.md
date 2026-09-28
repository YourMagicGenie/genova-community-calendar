# Genova Community Calendar: project scope and launch criteria

## Goal

Create a Genova-first event discovery calendar that saves people from checking many local websites. Collect public listings from publishers, institutions, venues, and event platforms; organize and deduplicate them; and offer a compact calendar that updates automatically in Google Calendar, Apple Calendar, and other iCalendar-compatible apps.

This document is the project's guiding definition of success. Implement it in small issues and pull requests. Adapt the existing Community Calendar pipeline where it already meets a requirement rather than rebuilding it. Preserve upstream attribution and the Apache 2.0 license.

## Intended experience

1. I open a Genova event page and see what is happening this week or weekend, with useful categories and links to original listings.
2. I subscribe to only the categories I want in my calendar. The subscription stays reasonably small and reflects event changes.
3. Before approving a UI or data change, I open a working preview link on my phone and inspect the result without asking someone to deploy it manually.

## Scope

### City and sources

- Start with Genova, using `Europe/Rome` dates and times.
- Define a configurable geographic boundary so nearby Ligurian events can be intentionally included or excluded.
- Audit Visitgenoa, Comune di Genova, Mentelocale Genova, Palazzo Ducale, theater and museum calendars, and relevant event platforms and organizers. These are candidates, not promises of compatible access.
- Record each source's name, URL, collection method, status, last successful update, event count, and access notes.
- Prefer an official ICS feed or API when available, then structured public event pages. Write a source-specific scraper where necessary. Include non-ICS sources.
- Preserve the publisher's name and a link to the original event page. Respect site access rules and rate limits; do not rely on login-protected or social-media scraping.

### Event quality and discovery

- Normalize title, start/end, timezone, venue/address, description, categories/tags, price or free-entry status if published, booking link, canonical event URL, and source metadata. Omit unknown facts rather than inventing them.
- Deduplicate the same event across publishers while retaining source attribution. Preserve separate performances and showtimes.
- Handle edits and cancellations. Flag uncertain or incomplete dates for review instead of publishing misleading times.
- Support music, theater/performance, art/exhibitions, sports, food/drink, festivals/markets, talks/workshops, family, outdoor/tours, and community/social. “Date night” is an additional tag that can coexist with a category. Allow curator corrections.
- Search and filter by date, category, and source. Show original links clearly.

### Calendar output and volume

- Publish read-only, category-specific ICS subscription URLs with stable event IDs.
- Refresh collected data at least daily once the Genova pipeline is configured. Calendar applications control when they poll a subscribed feed, so display updates may lag publication.
- Use a configurable upcoming-event window, initially 60 days.
- Exclude ordinary opening hours and generic season announcements. Represent a continuous exhibition as one multi-day event rather than one entry per day.
- Let users subscribe to selected categories instead of forcing the entire raw catalog into one calendar.

### Maintenance and review

- Show failed and stale sources, and allow them to be disabled.
- Document how to add and validate a source.
- Establish a separate preview environment with non-production configuration or sample data. Each pull request that changes the UI or event output must include a clickable preview URL and concise review steps. The link must work on a phone before the pull request is merged.
- Document the production URL and the path from approved pull request to production.
- Do not expose service keys or enable the fork's scheduled upstream city jobs before configuring Genova's sources, backend, and expected operating costs.

## Suggested implementation order

1. **Fork setup and preview:** Audit dependencies and costs, decide the lowest-maintenance hosting and backend configuration, and provide a working Genova preview with sample events.
2. **Source audit and vertical slice:** Connect a small varied set of real Genova sources, including a non-ICS source, through the existing normalization pipeline.
3. **Quality and discovery:** Add and verify deduplication, timezone handling, categories, location filtering, and volume controls.
4. **Subscriptions and operations:** Provide category ICS feeds, event change handling, scheduled refresh, source health, and owner instructions.

## Acceptance criteria for the first usable release

- [ ] A Genova event page and separate preview link are accessible on mobile; pull requests affecting visible output include a working preview link before merge.
- [ ] `Europe/Rome` is applied consistently, including daylight-saving transitions, with no invented start times.
- [ ] At least five independent Genova-area sources work across official/tourism listings, a local publisher, and a direct venue or organizer. At least one working source uses a non-ICS collection method. Any substitutions and their reasons are documented.
- [ ] Every published event has a source name and a working link to the original event listing.
- [ ] The listing can be filtered by date and the requested categories, including a “date night” tag.
- [ ] Duplicate publisher listings display as one event with attribution preserved; separate showtimes stay separate.
- [ ] Multi-day exhibitions do not create a separate all-day entry for each day. Ordinary opening hours and generic season pages do not flood the calendar.
- [ ] Valid category ICS feeds can be subscribed to in Google Calendar and Apple Calendar. Stable IDs allow an edited event to update without creating a duplicate.
- [ ] Updates and cancellations from sources reach the published feed after collection, subject to the calendar client's polling schedule.
- [ ] Collection runs at least daily once enabled, and failed or stale sources are visible to the maintainer without silently erasing valid events from other sources.
- [ ] The repository documents setup, preview, source addition, validation, ongoing costs, and review/release steps.

## Outside the first release

Ticket purchasing, RSVP management, personal accounts, personalized AI scoring, comprehensive social-media ingestion, and expansion to other cities.

## References

- Upstream project: https://github.com/judell/community-calendar
- Candidate Genova sources:
  - https://www.visitgenoa.it/it/eventi
  - https://www.comune.genova.it/vivere-il-comune/eventi
  - https://www.mentelocale.it/genova/eventi/
  - https://palazzoducale.genova.it/eventi/
