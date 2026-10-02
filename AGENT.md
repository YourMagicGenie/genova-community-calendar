# Genova event agent operating contract

This file defines the operating rules for a future Genova event-discovery agent. It is not a running agent, a source approval, or permission to scan websites. Until the admin-only controls and approved-source workflow in Issue #5 are implemented, do not run collection or connect credentials.

## Pilot boundary and purpose

- Start within the Comune di Genova. Include nearby Ligurian locations only after the maintainer explicitly approves a geographic expansion.
- Find enjoyable public activities for residents and visitors: music, theatre, art, sports, food and drink, festivals and markets, workshops, family activities, outdoor activities, tours, and community events.
- Do not prioritize government meetings, ordinary opening hours, generic season announcements, or listings without a specific public event.
- Discovery is best-effort over public and indexable information. Never promise complete coverage.

## Source discovery and approval

- Look for publishers, venues, organizers, institutions, event platforms, and directories that publish relevant events in the pilot area.
- For every candidate, record its name, canonical publisher URL, evidence that it publishes relevant Genova events, likely event types, geographic fit, proposed collection method, access or rate-limit notes, and the reason it was discovered.
- Prefer, in order: an official ICS feed or API; a structured public event page; then a source-specific method that respects the publisher's published access rules.
- Keep discovery separate from collection. A URL, search result, source suggestion, pull request, or merge is never approval to scan.
- Collect event data only from sources that the maintainer has explicitly approved and that the source directory marks `active`. If approval state cannot be checked, stop without collecting.
- Do not bypass login walls, paywalls, technical controls, or rate limits. Do not scrape private or login-protected social content. If access rules are unclear, leave the source pending for maintainer review.

## Event record

For each event, preserve the publisher and original event URL. Return these fields when available:

- title;
- start and end date/time in `Europe/Rome`, including the correct UTC offset;
- venue and location within the approved geography;
- a short description based on the source;
- price or free-entry status only when stated by the publisher;
- booking or ticket link when provided;
- one or more category guesses and confidence;
- the source name, canonical URL, and collection method;
- a brief evidence note pointing to the source detail used.

Leave missing or ambiguous details blank/null and flag them for review. Never invent a date, time, venue, price, booking link, or source attribution.

## Categories and confidence

Use the stable keys in [the Genova category contract](docs/genova-category-taxonomy.md):

- `music`
- `theatre-performance`
- `art-exhibitions`
- `sports`
- `food-drink`
- `festivals-markets`
- `talks-workshops`
- `family`
- `outdoors-tours`
- `community-social`

Multiple categories may apply. `date-night` is an optional extra tag, never a replacement for a category. Do not create new category keys. Mark unknown, unmapped, or low-confidence classifications for maintainer review; do not silently exclude uncertain events.

## Quality, duplicates, and failures

- Merge duplicate listings for the same event while preserving source attribution. Keep distinct performances and showtimes separate.
- Represent a continuous multi-day exhibition or festival as one event when the source supports that interpretation; do not create one listing per day.
- Preserve updates and cancellations from sources. Do not let a failure at one source erase valid events collected from another source.
- Record source failures and stale results for maintainer review. Do not mark a failed source healthy or imply a complete scan.
- Before publication, require valid event dates, approved geography, a source link, an active approved source, and review of uncertain data. Keep the public listing volume useful rather than flooding dates with hours or duplicate entries.

## Access, credentials, and costs

- Use public pages and approved unauthenticated feeds by default.
- Never put secrets, service-role keys, personal access tokens, or private source credentials in this file, event records, logs, or client-side code.
- Do not enable paid AI, search, scraping, or hosting services; recurring scans; or scheduled agent runs unless the maintainer has reviewed expected cost, quotas, access, and recovery steps and explicitly approved them.
- Enforce admin authorization on the server for discovery triggers, source decisions, run history, and corrections. A hidden button or private-looking page is not authorization.
- Follow [the source review and access rules](docs/genova-source-review.md).

## Run output

When the approved admin workflow exists, each run should report its trigger and time, this instruction file's version/commit, candidates discovered, approved active sources scanned, events added/updated/cancelled, items needing review, and source-level failures. Do not expose private review notes or admin run history on the public calendar.

The Issue #5 fixture workflow is the only current run path: it validates
fictional fixtures, scans no websites, and writes no events. It does not yet
implement source discovery, a review queue, collection, or calendar publishing.
Use this file as the agent's reviewed operating contract; do not treat the
fixture workflow as permission to collect from any source.