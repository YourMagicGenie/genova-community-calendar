# Genova agent run history and fixture test

Issue #5 needs private, reviewable run history for admin-triggered discovery and
collection. The existing `agent_runs` migration provides the ledger; the first
admin workflow uses it only for a fictional fixture check.

## Recorded for each run

- Mode and state.
- Requesting Supabase Auth user UUID.
- Full Git commit SHA used for the versioned `AGENT.md`.
- Queue, start, and finish times.
- Candidate, scanned-source, event, and review counts.
- Safe source-level failure summaries and an overall error summary.

Only a registered admin can read rows through an authenticated session.
Authenticated browser clients cannot create, edit, or delete run history.
Trusted Edge Function code makes privileged changes. A partial unique index
allows at most one queued or running job at a time.

## What the first workflow does

The admin page at `xmlui/admin.html` signs in with Supabase Auth, checks the
signed-in user's UUID against `admin_users`, and then shows private run history.
The only available button starts `mode=fixture`.

GitHub Actions validates two checked-in fictional Genova events and reports the
counts to the private Supabase callback. A successful fixture run reports one
fictional candidate, two fictional events, and one low-confidence item needing
review. It scans zero websites and adds, updates, or cancels zero public events.
It does not discover sources or use an AI provider. The public calendar remains
on its existing fictional preview.

The run endpoint uses `@supabase/server` to validate a real user session and
then checks the server-owned admin UUID allowlist. The callback endpoint uses a
separate random credential and only accepts the fixed fixture result fields.
Callback delivery retries temporary network and server errors. If a completion
callback still cannot be recorded, the workflow tries to report failure; a
later admin run marks any in-flight record older than 15 minutes as failed.
Repeated callbacks are safe, and late callbacks cannot reopen a finished run.
Neither the public page nor the GitHub runner receives a Supabase secret key.

## Owner setup needed before the first remote test

The repository contains the code, but the hosted project still needs its
application schema, Edge Functions, and owner-managed credentials. The
dashboard-created automatic-RLS helper is already applied; the application
migrations are not. The public key in `xmlui/config.json` is publishable and is
not an admin credential.

1. Apply the repository's database migrations to the owner-controlled Genova
   project and deploy `genova-agent-run` and `genova-agent-callback`. Check
   migration history before applying the pending schema; do not copy secrets
   into the repository or this document.
2. In Supabase Dashboard → Authentication → Users, create the owner's sign-in
   account using the owner's email and a new password. Copy that user's UUID.
3. In the Supabase SQL Editor, register only that UUID as admin:

   ```sql
   insert into public.admin_users (user_id)
   values ('PASTE-THE-AUTH-USER-UUID-HERE')
   on conflict (user_id) do nothing;
   ```

   The admin page displays the private handle `YMGAdmin`; it does not use a
   shared username or trust editable profile metadata.
4. Create a fine-grained GitHub personal access token limited to this repository,
   with `Actions: write` and `Contents: read`. Save it only as the Supabase
   Edge Function secret `GENOVA_AGENT_GITHUB_TOKEN`.
5. Generate a separate random callback credential. Store the same value as the
   Supabase Edge Function secret `GENOVA_AGENT_CALLBACK_SECRET` and the
   `GENOVA_AGENT_CALLBACK_TOKEN` secret in GitHub's `genova-agent-main`
   environment. In that environment's deployment branch rules, allow only the
   `main` branch. Do not store the callback token as a repository-level secret,
   send either secret in chat, or commit it.
   If you previously added `GENOVA_AGENT_CALLBACK_TOKEN` under repository
   **Settings → Secrets and variables → Actions → Repository secrets**, delete
   that repository-level copy; the environment-level secret is the only copy
   the fixture workflow needs.
6. After GitHub Pages publishes the merged files, open
   `https://yourmagicgenie.github.io/genova-community-calendar/xmlui/admin.html`,
   sign in, and select **Run fixture check**. The private history should show
   `succeeded`, 0 sources scanned, 2 fixture events, and 0 events written.

A source-specific collection test is a later step. It still needs the owner's
explicit approval of a public Genova source and its collection method. No
schedule, paid discovery service, source scan, or live event publication is
enabled by the fixture workflow.

## Tests

- `supabase/tests/test_genova_agent_runs.sql` checks table shape, the
  in-flight guard, explicit grants, and admin/non-admin row visibility using
  fictional users.
- `tests/genova-agent-protection.test.mjs` checks that only an authenticated
  allowlisted admin may request fixture mode, stale-run recovery, idempotent
  callback delivery, and that callbacks cannot claim source scans or public
  event writes.
- `tests/test_genova_agent_fixture.py` checks the offline fictional fixture,
  explicit Genova city field, and workflow's main-only environment boundary.
- `tests/test_genova_agent_callback.py` checks retry of transient callback
  failures and immediate failure on permanent rejection.
