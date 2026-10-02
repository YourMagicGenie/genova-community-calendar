# Supabase Migrations

`supabase/migrations/` is the ordered database change history for this
repository. A migration may alter existing data or objects, so never assume
that it is safe to paste into the SQL Editor more than once.

## Before applying changes to a hosted project

Use the Supabase CLI migration workflow from the repository root. First inspect
the local and remote versions:

```bash
supabase login
supabase link --project-ref <your-project-ref>
supabase migration list
```

Review the listed local and remote versions before applying anything. Apply
migrations only after confirming that each missing migration is intended for
that database:

```bash
supabase db push
```

For local testing, use a disposable local Supabase instance:

```bash
supabase start
supabase db reset
supabase test db supabase/tests/
```

`supabase db reset` resets the local database. Do not run it against the
hosted project.

## This project's current hosted migration state

As of 2026-10-02, the owner-controlled Genova project records the dashboard
RLS-helper migration at version `20261002104614`. The repository filename now
matches that applied version. The earlier application migrations, including
the application schema and `agent_runs`, have not been applied to that project.

Because a later migration is already recorded while earlier repository
migrations are pending, do not run `supabase db push` or paste SQL files into
the hosted SQL Editor until the migration list and the intended repair/apply
sequence have been reviewed. Issue [#45](https://github.com/YourMagicGenie/genova-community-calendar/issues/45)
tracks corrections to the operating instructions; Issue
[#5](https://github.com/YourMagicGenie/genova-community-calendar/issues/5)
tracks the admin-only fixture run that depends on the application schema.

Migration repair is an administrative history operation. Use it only after
confirming the actual remote schema and deciding which migration versions
really ran. Never copy a repair version from an example or another project.

## Rules for future schema changes

1. Add one timestamped migration file for each schema change.
2. Test it with local Supabase and the database tests before proposing a PR.
3. Apply it to the hosted project through the reviewed migration workflow.
4. Verify the database behavior and Supabase security/performance advisors.
5. Update this guide if the documented hosted migration state changes.

The older files in `supabase/ddl/` are snapshots or inherited setup material;
they are not a safe substitute for the ordered migrations in this directory.
