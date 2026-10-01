# Genova agent run history foundation

Issue #5 requires private, reviewable run history for future discovery and collection runs. This migration adds the database ledger and access boundary that those controls will use.

## Stored for each run

- Mode: discovery, collection, or fixture test.
- State: queued, running, succeeded, partial, failed, or cancelled.
- Requesting Supabase Auth user UUID, when available.
- Full Git commit SHA for the versioned `AGENT.md` instructions.
- Queue, start, and finish times.
- Candidate, scanned-source, event, and review counts.
- Safe source-level failure summaries and an overall error summary.

Only a registered admin can read rows through an authenticated session. Authenticated browser clients cannot create, edit, or delete run history; trusted server-side code uses the service role for those operations. A partial unique index allows at most one queued or running job at a time.

## Current limits

This is a storage and security foundation, not a running agent. There is no owner Supabase project configured, admin sign-in, discovery provider, remote trigger, or live collection. The migration has not been applied to any hosted project. No source is approved or active. Keep the public preview fixture-only until the remaining Issue #5 controls are implemented and a real source is approved.

The database test `supabase/tests/test_genova_agent_runs.sql` checks the table shape, in-flight guard, role grants, and admin/non-admin row visibility using fictional users. It does not contact any external service.
