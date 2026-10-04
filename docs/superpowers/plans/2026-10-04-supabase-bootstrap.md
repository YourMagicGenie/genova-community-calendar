# Genova Supabase bootstrap workflow plan

## Goal

Create a one-time manual workflow to preview and apply the missing repository
migrations to the connected Genova project, with fail-closed preflight and
postflight checks. Do not create users, deploy functions, or scan sources here.

## Files and responsibilities

- .github/workflows/supabase-bootstrap.yml: main-only manual preview/apply
  flow using the project's protected Actions environment.
- supabase/ops/genova_bootstrap_state.sql: read-only snapshot of remote
  migration versions, public relations, RLS-enabled tables, and Auth users.
- scripts/verify_genova_supabase_bootstrap.py: rejects unexpected starting
  state and verifies migrations/tables/RLS after apply.
- tests/test_supabase_bootstrap_guard.py: covers accepted and rejected
  preflight/postflight states.
- docs/genova-supabase-bootstrap.md: owner setup and run steps.
- supabase/migrations/README.md and CHANGELOG.md: record the reviewed path and
  current state.

## Implementation and verification

1. Write tests for the accepted empty project, unexpected migration history,
   existing public tables/users, completed migration history, required tables,
   and RLS checks.
2. Run the tests before implementation and confirm they fail because the guard
   does not exist.
3. Add the read-only SQL snapshot and fail-closed Python verifier.
4. Add a manual workflow with a dry-run default and explicit apply input; pin
   the Supabase CLI version and restrict secrets to the project environment.
5. Document the owner-only setup and update the changelog.
6. Run the focused test, Python compilation, YAML validation, full project
   checks in GitHub Actions, and review the workflow diff before merge.

## Safety behavior

Unexpected remote state stops before db push. Apply runs only when manually
selected, uses --include-all, and verifies the complete migration history.
The action must never reset the remote database or rewrite migration history.
