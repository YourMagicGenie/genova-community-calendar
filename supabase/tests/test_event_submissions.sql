BEGIN;
SELECT plan(20);

SELECT ok((SELECT relrowsecurity FROM pg_class WHERE oid = 'public.event_submissions'::regclass),
  'submission queue has RLS');
SELECT ok(NOT has_table_privilege('anon', 'public.event_submissions', 'SELECT'),
  'anonymous users cannot read proposals');
SELECT ok(NOT has_table_privilege('anon', 'public.event_submissions', 'UPDATE'),
  'anonymous users cannot change proposals');
SELECT ok(NOT has_table_privilege('authenticated', 'public.event_submissions', 'DELETE'),
  'signed-in users cannot erase review history');
SELECT ok(has_column_privilege('anon', 'public.event_submissions', 'title', 'INSERT'),
  'visitor can propose an event title');
SELECT ok(NOT has_column_privilege('anon', 'public.event_submissions', 'status', 'INSERT'),
  'visitor cannot set approval state');
SELECT ok(NOT has_column_privilege('authenticated', 'public.event_submissions', 'status', 'UPDATE'),
  'even an admin browser cannot directly set approval state');
SELECT ok(NOT has_function_privilege('anon', 'public.review_event_submission(uuid,text)', 'EXECUTE'),
  'anonymous users cannot call review function');

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('00000000-0000-0000-0000-000000000068', 'authenticated', 'authenticated',
   'submission-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000000069', 'authenticated', 'authenticated',
   'submission-visitor@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now());
INSERT INTO public.admin_users(user_id) VALUES ('00000000-0000-0000-0000-000000000068');

SET LOCAL ROLE anon;
SELECT throws_ok($$INSERT INTO public.event_submissions (title, start_time, description, rights_confirmed)
  VALUES ('Closed intake test', '2026-11-01T18:00:00+01:00', 'A complete original event description.', true)$$,
  '42501', 'community event intake is not enabled',
  'applying the schema does not open the direct public intake API');
RESET ROLE;
UPDATE public.community_submission_settings SET accepting = true WHERE singleton;

SET LOCAL ROLE anon;
INSERT INTO public.event_submissions (title, start_time, description, rights_confirmed)
VALUES ('Community test event', '2026-11-02T18:00:00+01:00', 'Original description for this example.', true);
RESET ROLE;
SELECT is((SELECT count(*)::int FROM public.event_submissions WHERE title = 'Community test event'), 1,
  'anonymous visitor created one private proposal');
SELECT is((SELECT status FROM public.event_submissions WHERE title = 'Community test event'), 'pending',
  'proposal begins pending');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000069', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000069","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.event_submissions WHERE title = 'Community test event'), 0,
  'non-admin cannot inspect pending proposals');
SELECT throws_ok($$SELECT public.review_event_submission(
  (SELECT id FROM public.event_submissions LIMIT 1), 'approve')$$,
  '42501', 'admin access required', 'non-admin cannot approve an event');
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000068', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000068","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.event_submissions WHERE title = 'Community test event'), 1,
  'admin can read proposal');
SELECT is(public.review_event_submission(
  (SELECT id FROM public.event_submissions WHERE title = 'Community test event'), 'approve'),
  'approve', 'admin approves proposal');
SELECT is((SELECT count(*)::int FROM public.event_submissions WHERE status = 'approved'
  AND title = 'Community test event'), 1, 'approval recorded');
RESET ROLE;
SELECT is((SELECT count(*)::int FROM public.events
  WHERE source_uid LIKE 'community:%' AND title = 'Community test event'), 1,
  'approval creates one stable community event');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000068', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000068","role":"authenticated"}', true);
UPDATE public.event_submissions SET title = 'Corrected community event'
WHERE title = 'Community test event';
RESET ROLE;
SELECT is((SELECT title FROM public.events WHERE source_uid LIKE 'community:%'
  AND title = 'Corrected community event' LIMIT 1), 'Corrected community event',
  'admin correction updates the published event');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000068', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000068","role":"authenticated"}', true);
SELECT is(public.review_event_submission(
  (SELECT id FROM public.event_submissions WHERE title = 'Corrected community event'), 'withdraw'),
  'withdraw', 'admin withdraws approved event');
RESET ROLE;
SELECT is((SELECT count(*)::int FROM public.events WHERE title = 'Corrected community event'), 0,
  'withdrawal removes the event record');

SELECT * FROM finish();
ROLLBACK;
