# Genova source review states

New feed and scraper registrations enter the `feeds` table as `pending`. This
records a proposal; it does not authorize collection. The collector reads only
rows whose status is `active` and stops if it cannot read the database approval
state.

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
