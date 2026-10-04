# One-time Genova Supabase schema bootstrap

This workflow prepares the existing Genova Supabase project for the Issue #5
fixture-only admin test. It applies the repository's database migrations. It
does not create an admin account, deploy Edge Functions, scan GenovaToday, or
publish events.

The workflow is deliberately one-time. Its preflight must see exactly one
recorded migration (20261002104614_revoke_anon_exec_on_rls_auto_enable), no
relations in the public schema, and no Auth users. If anything differs, it
stops before changing the database.

## Before running it

In the GitHub repository:

1. Open **Settings → Environments** and create **genova-supabase-bootstrap**.
2. Restrict deployments from that environment to the **main** branch.
3. Add these two environment secrets:
   - **SUPABASE_ACCESS_TOKEN**: create a personal access token from [Supabase Account → Access Tokens](https://supabase.com/dashboard/account/tokens) while signed in to an account with access to the Genova project. Scope the token to this project and grant **Read** for all six: **Project Settings**, **API Keys**, **API Key Secrets**, **Connection Pooling**, **Database**, and **Advisors**. The first three let `supabase link` read project configuration and keys. Connection Pooling lets it cache the IPv4 pooler URL used by GitHub's runner. Database permits the read-only preflight/postflight SQL query; Advisors permits the security report.
   - **SUPABASE_DB_PASSWORD**: the database password chosen when the project was created.
4. Do not paste either value into an issue, PR, chat, workflow input, or source file.

The workflow has read-only repository permissions, checks out main without
retaining the GitHub token, and links only to project
eginljyhnnczeeqxwfia.

## Run the preview

1. Open **Actions → Bootstrap Genova Supabase schema → Run workflow**.
2. Select branch **main**.
3. Leave **operation** set to **preview**.
4. Review the run. It validates the empty starting state, checks Security
   Advisor access, and prints the migration history and complete dry-run list
   for `supabase db push --include-all`. It does not apply migrations.

A `403` with `missing_permissions: ["database_read"]` at the state query means
**Database → Read** is missing; a `403` at the advisor check means **Advisors →
Read** is missing. If no IPv4 pooler URL was cached, **Connection Pooling →
Read** is missing or the pooler is unavailable. Create one replacement token
with all six Read permissions above, replace the GitHub environment's
`SUPABASE_ACCESS_TOKEN` secret, and rerun preview. The database password does
not need another reset. If the database-state preflight reports unexpected
schema, migration history, or Auth users, stop and review the remote state;
do not edit the guard or reset the database.

## Apply after the preview

After the preview shows the expected repository migrations, run the workflow
again from main and choose **operation: apply**. It repeats the preflight,
prints the migration dry run, applies the migrations with
`supabase db push --include-all`, then confirms:

- every local migration version is present remotely;
- the application tables needed by the admin flow exist;
- Row Level Security is enabled on the admin, source, event, and run-history
  tables; and
- no Auth user was created as part of the schema change.

The workflow then prints the Supabase Security Advisor findings. Review them
in the Actions run before proceeding to the fixture test; `--fail-on none`
shows findings without treating the report itself as an automatic migration
failure.

This does not use `db reset --linked`, migration repair, or direct SQL edits to
migration history. Supabase's `--include-all` option is used because the project
already records a later RLS-helper migration while earlier repository
migrations remain unapplied.

## After it succeeds

Stop using this one-time workflow. It intentionally refuses to run again once
the project no longer matches its original empty state. The next steps are to
deploy the Issue #5 Edge Functions, configure the owner Auth identity and
secrets, and run the fictional fixture from the admin page. A real source scan
requires its own source review and remains disabled.
