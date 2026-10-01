# Initial Genova source candidate audit

**Reviewed:** 2026-10-01  
**Status:** Discovery notes only. None of these sources is approved or active.

This is a small research snapshot for the maintainer, not the operational source directory. I inspected public event index pages and their descriptions. I did not collect event records, run a scraper, or confirm an ICS/API endpoint. Publisher terms, `robots.txt`, and acceptable request rates have not been reviewed; each candidate must remain pending until those checks and maintainer approval are recorded in the source directory.

| Candidate | Why it may fit | Observed information | Proposed next check | Current disposition |
| --- | --- | --- | --- | --- |
| [Visitgenoa — Eventi](https://www.visitgenoa.it/it/eventi) | City tourism listings cover cultural events, exhibitions, family activities, tours, and longer-running programs. | The public index shows event links, date ranges, and labels including culture, exhibitions, family, tours, and top events. | Check for an official feed/API or structured event data, then review publisher rules before considering a low-rate public-page method. Compare with the organizer's page to retain the most authoritative event link. | Pending access and method review |
| [Mentelocale — Genova events](https://www.mentelocale.it/genova/eventi/) | Local editorial agenda with music, art, sport, markets, tours, talks, and other activities; a strong candidate for varied discovery beyond institutional feeds. | The index shows dated event links and topic labels. It also includes some events outside the Comune di Genova, so location filtering is essential. | Check publisher rules and any feed/API first. If permitted, assess index-plus-detail-page extraction and apply the Comune di Genova boundary. Keep original publisher and organizer links. | Pending access and method review |
| [Palazzo Ducale — event calendar](https://palazzoducale.genova.it/calendario-eventi/) | Direct source for exhibitions, talks, workshops, and public cultural programs at Palazzo Ducale and Wolfsoniana. | Listing cards expose titles, venue, date ranges, times, admission notes, and ticket links. Multi-day exhibitions appear in the date-based calendar, so they must normalize to one event rather than one copy per day. | Check for an official feed/API or structured data and review publisher rules. Test a fixture for multi-day dates and distinguish separate timed events from opening periods. | Pending access and method review |
| [Teatro Nazionale di Genova — season](https://www.teatronazionalegenova.it/stagione-2026-2027/) | Direct theater operator covering several Genova stages; useful for performances, family theater, and cultural events. | The official site lists the 2026/27 season and stage filters. Event-level dates and venues should be checked on individual production pages; the listing's presentation may need inspection for accessible structured data. | Check publisher rules and feed/API availability. Verify event-level showtimes and each venue's Comune di Genova location before considering collection. | Pending access and method review |
| [Musei di Genova — Mostre ed Eventi](https://www.museidigenova.it/it/mostre-ed-eventi) | Official civic museum listings include exhibitions, workshops, talks, family activities, and guided visits across city museums. | The public index shows start/end dates and venues. Its event cards often link to Visitgenoa, so overlap with that publisher is expected and canonical-link deduplication will matter. | Review the museum and linked publisher rules. Check whether the museum offers a distinct feed/API; otherwise decide whether this adds enough direct-source value beyond Visitgenoa. | Pending access and method review |


## Preliminary public-use review

**Checked:** 2026-10-01. These notes are a starting point, not legal advice or source approval.

- [Visitgenoa credits](https://www.visitgenoa.it/it/credits) identifies Visitgenoa as a Comune di Genova project and says some images/content are used with permission from their respective rights holders. This is not a blanket reuse license. The [Comune's legal notice](https://www.comune.genova.it/note-legali) says its own site's material is generally CC BY 4.0 unless otherwise specified, including third-party content; do not assume that license applies to Visitgenoa items or embedded publisher material.
- Mentelocale event pages show a copyright notice reserving rights. Its [privacy notice](https://www.mentelocale.it/informativa-privacy.htm) is about personal-data processing, not permission to republish editorial content. Before automated extraction, ask Mentelocale about an official feed/API or written collection and attribution terms. Do not copy article text or images into the calendar.
- Teatro Nazionale's [site policy](https://www.teatronazionalegenova.it/policy-sito.htm) describes navigation and personal-data handling; it does not answer whether automated event collection is allowed. Ask about an official feed/API or use terms before building a collector.
- Palazzo Ducale's public [event calendar](https://palazzoducale.genova.it/calendario-eventi/) provides useful event facts. The site's available regulation page covers use of the physical venue, not automated use of website content; web collection terms remain unverified.
- Musei di Genova's event cards often link to Visitgenoa, creating likely duplication. A separate legal notice on `catalogo.museidigenova.it` restricts public/commercial reuse of catalogue text and images, but that notice is on the catalogue subdomain; do not assume it automatically governs the separate event listing. Clarify with the Comune before collection.

No source's `robots.txt`, official event feed/API, request limits, or automated-collection permission has been confirmed in this review.

## Suggested order for maintainer review

Start with direct venue/organizer sources if their terms or an explicit permission allow collection: Palazzo Ducale and Teatro Nazionale look useful for authoritative dates, venues, and ticket details. Visitgenoa may add broader event coverage but needs rights and overlap checks. Mentelocale looks especially useful for variety, but its editorial rights notice makes a feed/permission conversation the prudent next step. Musei di Genova may overlap with Visitgenoa and should be kept only if it contributes distinct events or a permitted direct feed.

This is a candidate-prioritization recommendation only. Every item remains pending until access terms and collection method are recorded and the maintainer explicitly approves it.

## Deliberately not shortlisted

The [Comune di Genova general events page](https://www.comune.genova.it/vivere-il-comune/eventi) describes council and committee convocations among its event content. That is a poor match for this fun-events calendar. Review specific cultural, museum, venue, or sports pages instead of collecting the general municipal meeting stream.

## Before any source can be activated

For each candidate, verify and record the access rules, `robots.txt`, rate limits, available official feed/API, collection method, geographic coverage, event fields, attribution target, and expected maintenance effort. Public visibility alone does not mean permission to collect. A review result must be entered into the admin source directory; discovery or this document never activates a source.

These notes support Issue #5's Genova-only, admin-reviewed discovery flow. The required first release still needs at least five independent sources, including one non-ICS source, but no candidate should be counted until its method works and a maintainer has approved it.