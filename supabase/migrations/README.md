# Supabase Migrations

`supabase/migrations/` is the version-controlled, ordered history of database
changes. Apply schema changes with the Supabase CLI; do not paste historical
migration files into the hosted SQL Editor or reset the hosted project.

## Local development and tests

Use a disposable local Supabase stack:

```bash
supabase start
supabase db reset
supabase test db supabase/tests/
```

`supabase db reset` is for the local stack only. Never run
`supabase db reset --linked` against the owner-controlled project.

## Current owner-controlled Genova project state

Checked on 2026-10-04: the project records only
`20261002104614_revoke_anon_exec_on_rls_auto_enable`. The `public` schema has
no application tables, and no Edge Functions are deployed. The earlier
repository migrations, including the event/source schema and private agent run
history, remain unapplied. No Auth users, real sources, or events have been
added.

The existing RLS-helper migration was applied before the application schema.
Do not remove its history or reset the project. The supported one-time
bootstrap is documented in
[`docs/genova-supabase-bootstrap.md`](../../docs/genova-supabase-bootstrap.md)
and implemented by the manually triggered
[`supabase-bootstrap.yml`](../../.github/workflows/supabase-bootstrap.yml)
workflow.

## One-time hosted bootstrap

The workflow checks the exact known starting state, previews all pending
repository migrations with `supabase db push --dry-run --include-all`, and
applies only when the owner manually selects `apply`. It verifies that every
local migration is then present and that required admin/source/event/run
tables have Row Level Security enabled.

The `--include-all` option is required because the project has a later
migration recorded while earlier repository migrations are still missing.
Do not use `migration repair`, direct SQL edits to migration history, or
`db reset --linked` for this project.

The workflow requires `SUPABASE_ACCESS_TOKEN` and `SUPABASE_DB_PASSWORD`
stored as secrets in the GitHub environment named
`genova-supabase-bootstrap`. Never put either value in GitHub issues, PRs,
chat, source files, or workflow inputs. If preflight detects any different
migration history, public relation, or Auth user, it stops without applying
migrations; review the remote state before proceeding.

## Future schema changes

1. Add one timestamped migration file for each schema change.
2. Test a clean local reset and `supabase test db supabase/tests/`.
3. Review the migration and RLS behavior before deployment.
4. Verify migration history, project tables, and Supabase security/performance
   advisors after deployment.
5. Update this guide when the hosted migration state changes.

Files in `supabase/ddl/` are inherited schema snapshots, not a substitute for
the ordered migration history.
