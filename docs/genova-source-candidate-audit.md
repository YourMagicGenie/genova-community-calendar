# Initial Genova source candidate audit

**Reviewed:** 2026-10-05  
**Status:** Discovery notes only. Giardini Luzzati / Spazio Comune is the owner's selected first-source candidate; no project collector has fetched it yet.

This is a small research snapshot for the maintainer, not the operational source directory. I inspected public event index pages and their descriptions. I did not collect event records, run a scraper, or confirm an ICS/API endpoint. Candidate review should distinguish use of basic event facts from reuse of publisher-created text, images, or a database. No candidate is approved for automated collection until its access method, location coverage, and request rate are recorded and a maintainer approves it.

| Candidate | Why it may fit | Observed information | Proposed next check | Current disposition |
| --- | --- | --- | --- | --- |
| [Giardini Luzzati / Spazio Comune](https://www.spazio-comune.org/) | Direct organizer for cultural events and community activity at the Giardini. | The official site exposes event/product listings. An official indexed event page shows “Nessuno ci insegna a cadere,” Tuesday 6 October 2026 at 18:00, at Giardini Luzzati - Spazio Comune; direct URL: https://www.spazio-comune.org/prodotto/nessuno-ci-insegna-a-cadere/. This was found through public search indexing, not fetched by the project collector. | First pilot: check the exact page path against the site's crawler rules, then make one bounded request only if allowed. Record title/date/time/location, publisher, and direct event link; do not retain the page description or image. | Owner-selected first-source candidate; live collector test pending #59/#49 and crawler-path check |
| [Visitgenoa — Eventi](https://www.visitgenoa.it/it/eventi) | City tourism listings cover cultural events, exhibitions, family activities, tours, and longer-running programs. | The public index shows event links, date ranges, and labels including culture, exhibitions, family, tours, and top events. | Identify the organizer's original event page where available. For a limited pilot, use only the minimum factual fields, write a fresh short summary from those facts, and link to the source. Check the relevant terms and technical access before automating. | Pending source review |
| [Mentelocale — Genova events](https://www.mentelocale.it/genova/eventi/) | Local editorial agenda with music, art, sport, markets, tours, talks, and other activities; a strong candidate for varied discovery beyond institutional feeds. | The index shows dated event links and topic labels. It also includes some events outside the Comune di Genova, so location filtering is essential. | A small facts-only pilot can test whether it adds useful events: retain title/date/time/venue/admission facts, write a concise summary in new wording, credit Mentelocale, and link directly to the event page. Do not copy its description or image. Check terms, technical access, and request rate before automating. | Pending source review |
| [Palazzo Ducale — event calendar](https://palazzoducale.genova.it/calendario-eventi/) | Direct source for exhibitions, talks, workshops, and public cultural programs at Palazzo Ducale and Wolfsoniana. | Listing cards expose titles, venue, date ranges, times, admission notes, and ticket links. Multi-day exhibitions appear in the date-based calendar, so they must normalize to one event rather than one copy per day. | Test a small facts-only sample and distinguish separate timed events from exhibition opening periods. Prefer the organizer's ticket/event page as the outbound link. Check terms and technical access before automating. | Pending source review |
| [Teatro Nazionale di Genova — season](https://www.teatronazionalegenova.it/stagione-2026-2027/) | Direct theater operator covering several Genova stages; useful for performances, family theater, and cultural events. | The official site lists the 2026/27 season and stage filters. Event-level dates and venues should be checked on individual production pages; the listing's presentation may need inspection for accessible structured data. | Verify dates and venues on individual production pages. A facts-only pilot can use original titles and schedules with a fresh one-line summary and a direct event link. Check terms and technical access before automating. | Pending source review |
| [Musei di Genova — Mostre ed Eventi](https://www.museidigenova.it/it/mostre-ed-eventi) | Official civic museum listings include exhibitions, workshops, talks, family activities, and guided visits across city museums. | The public index shows start/end dates and venues. Its event cards often link to Visitgenoa, so overlap with that publisher is expected and canonical-link deduplication will matter. | Compare a small sample with Visitgenoa and retain the more direct organizer link. Use factual event details and an independently written summary; check the terms for the specific event site before automation. | Pending source review |

## Preliminary public-use review

**Checked:** 2026-10-01. These notes are a practical starting point, not legal advice or a final rights determination.

- [Visitgenoa credits](https://www.visitgenoa.it/it/credits) identifies Visitgenoa as a Comune di Genova project and says some images/content are used with permission from their respective rights holders. This is not a blanket reuse license. The [Comune's legal notice](https://www.comune.genova.it/note-legali) says its own site's material is generally CC BY 4.0 unless otherwise specified, including third-party content; do not assume that license applies to Visitgenoa items or embedded publisher material.
- Mentelocale event pages show a copyright notice reserving rights. That notice means the calendar should not copy their expressive descriptions or assume their photos are reusable. It does not, by itself, tell us whether a low-volume facts-only event index using public pages is allowed. For a small pilot, test only basic event facts, write a genuinely fresh compact summary, credit Mentelocale, and link directly to its event page. Do not reproduce or closely paraphrase its description or download/display its cover image without a license or permission.
- Teatro Nazionale's [site policy](https://www.teatronazionalegenova.it/policy-sito.htm) describes navigation and personal-data handling; it does not answer whether automated event collection is allowed. Check for a separate applicable collection rule before automating. A limited facts-only review can still establish whether the source is useful.
- Palazzo Ducale's public [event calendar](https://palazzoducale.genova.it/calendario-eventi/) provides useful event facts. The site's available regulation page covers use of the physical venue, not automated use of website content; web collection terms remain unverified.
- Musei di Genova's event cards often link to Visitgenoa, creating likely duplication. A separate legal notice on `catalogo.museidigenova.it` restricts public/commercial reuse of catalogue text and images, but that notice is on the catalogue subdomain; do not assume it automatically governs the separate event listing.

## Practical pilot rules

This calendar is a facts-and-links index. Store the event title, date/time and
location when listed, publisher name, and direct event URL. Do not copy
descriptions, photographs, or promotional text. The event page remains the
source for full details, access requirements, and changes.

The owner's whitelist controls which publishers are considered for collection.
For each active source, configure only the public event index needed for the
calendar. Check the exact path against the site's crawler instructions before
a run; skip a disallowed path, do not evade the rule through another route, and
continue the other sources. Treat an HTTP 404 for robots.txt as no published crawler rules and continue under the low request limit. If the robots request returns 401/403/429/5xx or a network error, skip that source for the run. A clear site-level no-automation rule
pauses that source. This practical policy is not a claim that robots.txt is
legal authorization or a blanket assessment of every possible database right.

Keep requests bounded: one initial listing page per source, sequentially; at
most one refresh per source per day; cache responses and use conditional
requests when supported; honor a published crawl delay; back off on rate limits
and server errors. Do not fetch every event detail page when the listing page
contains the facts needed to place an event in the calendar.

EU database rights can apply to substantial or repeated systematic extraction
in some circumstances. This is a reason to keep the collection proportionate
and to stop if a source objects, not a reason to require a bespoke legal memo
for every event title. For significant scaling or a clear dispute, get
appropriate legal advice.

`robots.txt` is a crawler protocol, not a form of access authorization (RFC
9309, https://www.rfc-editor.org/rfc/rfc9309.html). Respecting it is the
project's operational courtesy rule. Do not confuse that courtesy with a
permission grant.

## Deliberately not shortlisted

The [Comune di Genova general events page](https://www.comune.genova.it/vivere-il-comune/eventi) describes council and committee convocations among its event content. That is a poor match for this fun-events calendar. Review specific cultural, museum, venue, or sports pages instead of collecting the general municipal meeting stream.

## Before any source can be activated

For each candidate, record the source URL, access method, geographic coverage, fields collected, request rate, attribution target, and review notes. Use an official feed/API when it is available and suitable; a low-rate public-page method can be evaluated for the facts-only pilot when the site's applicable terms and technical controls allow it. Discovery or this document never activates a source.

These notes support Issue #5's Genova-only, admin-reviewed discovery flow. The required first release still needs at least five independent sources, including one non-ICS source, but no candidate should be counted until its method works and a maintainer has approved it.
