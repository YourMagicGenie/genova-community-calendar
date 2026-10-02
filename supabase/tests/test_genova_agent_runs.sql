-- Agent run history is private and writable only by trusted server code.
BEGIN;
SELECT plan(31);

SELECT has_table('public', 'agent_runs', 'agent run history table exists');
SELECT has_column('public', 'agent_runs', 'run_mode', 'run mode is recorded');
SELECT has_column('public', 'agent_runs', 'status', 'run status is recorded');
SELECT has_column('public', 'agent_runs', 'requested_by', 'requesting admin is recorded');
SELECT has_column('public', 'agent_runs', 'instruction_revision', 'agent instruction revision is recorded');
SELECT has_column('public', 'agent_runs', 'queued_at', 'request time is recorded');
SELECT has_column('public', 'agent_runs', 'started_at', 'start time is recorded');
SELECT has_column('public', 'agent_runs', 'finished_at', 'completion time is recorded');
SELECT has_column('public', 'agent_runs', 'candidate_count', 'candidate count is recorded');
SELECT has_column('public', 'agent_runs', 'sources_scanned', 'approved source scan count is recorded');
SELECT has_column('public', 'agent_runs', 'events_found', 'found event count is recorded');
SELECT has_column('public', 'agent_runs', 'events_needing_review', 'review count is recorded');
SELECT has_column('public', 'agent_runs', 'source_failures', 'source-level failures are recorded');

SELECT ok(
  (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.agent_runs'::regclass),
  'row level security is enabled on agent run history'
);
SELECT ok(
  (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.admin_users'::regclass),
  'row level security is enabled on the admin allowlist'
);
SELECT ok(
  to_regclass('public.agent_runs_one_inflight_idx') IS NOT NULL,
  'a partial unique index prevents overlapping queued or running jobs'
);
SELECT ok(
  NOT has_table_privilege('anon', 'public.agent_runs', 'SELECT'),
  'anonymous visitors cannot read agent run history'
);
SELECT ok(
  has_table_privilege('authenticated', 'public.admin_users', 'SELECT'),
  'signed-in sessions can check their own admin marker'
);
SELECT ok(
  has_table_privilege('service_role', 'public.admin_users', 'SELECT'),
  'trusted Edge Functions can check the admin allowlist'
);
SELECT ok(
  NOT has_table_privilege('anon', 'public.admin_users', 'SELECT'),
  'anonymous visitors cannot query the admin allowlist'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.admin_users', 'INSERT'),
  'signed-in users cannot grant admin access'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.admin_users', 'UPDATE') AND
  NOT has_table_privilege('authenticated', 'public.admin_users', 'DELETE'),
  'signed-in users cannot change or revoke admin access'
);
SELECT ok(
  has_table_privilege('service_role', 'public.agent_runs', 'INSERT'),
  'trusted server code can create run records'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.agent_runs', 'INSERT'),
  'signed-in users cannot create run records directly'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.agent_runs', 'UPDATE'),
  'signed-in users cannot alter run records directly'
);
SELECT ok(
  NOT has_table_privilege('authenticated', 'public.agent_runs', 'DELETE'),
  'signed-in users cannot delete run history'
);

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('00000000-0000-0000-0000-000000000051', 'authenticated', 'authenticated',
   'genova-run-non-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000000055', 'authenticated', 'authenticated',
   'genova-run-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.admin_users(user_id)
VALUES ('00000000-0000-0000-0000-000000000055')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO public.agent_runs (
  run_mode, status, requested_by, instruction_revision
) VALUES (
  'discover', 'queued', '00000000-0000-0000-0000-000000000055',
  '0000000000000000000000000000000000000005'
);

SELECT throws_ok(
  $$INSERT INTO public.agent_runs (run_mode, status, instruction_revision)
    VALUES ('collect', 'queued', '0000000000000000000000000000000000000005')$$,
  '23505',
  'duplicate key value violates unique constraint "agent_runs_one_inflight_idx"',
  'a second in-flight run is rejected'
);

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000051', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000051","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.agent_runs), 0,
  'authenticated non-admin cannot inspect run history');
SELECT is((SELECT count(*)::int FROM public.admin_users), 0,
  'authenticated non-admin cannot see the admin marker');
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000055', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000055","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.agent_runs), 1,
  'registered admin can inspect run history');
SELECT is((SELECT count(*)::int FROM public.admin_users), 1,
  'registered admin can see their own admin marker');
RESET ROLE;

DELETE FROM public.agent_runs;
DELETE FROM public.admin_users WHERE user_id = '00000000-0000-0000-0000-000000000055';
DELETE FROM auth.users WHERE id IN (
  '00000000-0000-0000-0000-000000000051',
  '00000000-0000-0000-0000-000000000055'
);

SELECT * FROM finish();
ROLLBACK;
