# Later Genova Supabase schema migrations

The one-time bootstrap in Issue #47 is complete and refuses to run again.
Use this workflow for one reviewed, timestamped migration at a time against
project `eginljyhnnczeeqxwfia`.

## Before the hosted run

1. Add the migration under `supabase/migrations/` and test a clean local
   database reset plus `supabase test db supabase/tests/` in the PR.
2. Merge only after GitHub Actions and Cloudflare checks pass.
3. Confirm the existing `genova-supabase-bootstrap` GitHub environment still
   restricts deployments to `main` and contains `SUPABASE_ACCESS_TOKEN`
   and `SUPABASE_DB_PASSWORD`. Do not paste either value into chat or logs.

## Preview, then apply

1. Open **Actions → Apply reviewed Genova Supabase migration → Run workflow**.
   Select **main** and `operation: preview`.
2. The job checks project linkage, the IPv4 pooler, remote migration history,
   core RLS, and that **exactly the newest local migration** is pending.
   Review the `supabase db push --dry-run` output. Preview makes no schema
   change.
3. Only after the dry run names the expected file, run the workflow again
   from **main** with `operation: apply`.
4. Review its final migration list, postflight history/RLS check, and Security
   Advisor findings. A green advisor step means the report was fetched, not
   that it contains zero findings.

The workflow deliberately stops if remote history differs, multiple migrations
are pending, or core RLS is missing. Do not edit migration history or use
`db reset --linked` to work around a stop; inspect the hosted state first.
The selected GitHub token grants Read scopes to link and query; the database
password authenticates `db push`. The public sample calendar remains fictional
until the separate admin fixture and source-review work is complete.
