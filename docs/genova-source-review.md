# Genova source review states

New feed and scraper registrations enter the `feeds` table as `pending`. This
records a candidate; it does not place it on the owner's collection whitelist.
The owner can promote selected staple publishers/venues to `active`. The
collector reads only `active` sources and stops if it cannot read that state.
An active source is still subject to path-level crawler rules at every run.

## Review information

The public `feeds` table retains the publisher page and discovery/collection
method. Private notes live in `feed_source_reviews`, including source
provenance, access notes, Genova fit, discovery reason, and the identity and
time of the latest review. Keeping these notes in a separate table matters:
row-level security filters rows, not columns, so notes on active sources would
otherwise be visible to the public.

Registration from `pending_feeds.txt` records only what that file proves; it
leaves Genova fit as `unknown` and access notes blank for the maintainer to
review.

## Statuses

| Status | Meaning | Collected? |
| --- | --- | --- |
| `pending` | Candidate awaiting a maintainer decision | No |
| `active` | Approved and enabled | Yes |
| `paused` | Approved source temporarily disabled | No |
| `rejected` | Reviewed and declined; retained for context | No |
| `removed` | Removed from use | No |

The existing admin allowlist protects source management through Supabase Row
Level Security. Public and ordinary signed-in users can read active rows only;
only an authenticated user present in `admin_users` can read candidate metadata
or change source rows. The frontend must never receive the service-role key.

The admin review page and live project connection are subsequent work under
Issue #5. Until an owner-controlled Supabase project is configured, these
migrations are exercised only by disposable local Supabase in GitHub Actions.

## Whitelist and crawler behavior

`active` means the maintainer selected the publisher for the calendar. It does
not authorize every page on the publisher's host. Configure a small set of
public event index URLs for each source, check `robots.txt` for each requested
path, skip disallowed paths, and continue other allowed sources. If the robots
file cannot be fetched reliably, skip only that source for the current run and
report the reason. A clearly published no-automation rule pauses that source.
Do not change hosts or paths to evade a restriction.

For the first pilot, request one listing page, store event title/date/time,
location when available, publisher name, and direct event URL, and do not copy
descriptions or images. Refresh no more than daily, sequentially, with caching,
conditional requests when supported, and backoff on rate limits or server
errors. This is a lightweight operating rule, not an event-by-event legal
approval workflow.