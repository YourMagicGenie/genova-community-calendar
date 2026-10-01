-- remove_feed bypasses table RLS, so only an authenticated admin may execute
-- its destructive event/source removal.
BEGIN;
SELECT plan(7);

SELECT ok(
  NOT has_function_privilege('anon', 'public.remove_feed(bigint)', 'EXECUTE'),
  'anonymous visitors cannot execute remove_feed'
);
SELECT ok(
  has_function_privilege('authenticated', 'public.remove_feed(bigint)', 'EXECUTE'),
  'authenticated users may call the function, which checks admin status internally'
);

INSERT INTO public.feeds (city, url, name, status, feed_type)
VALUES ('genova', 'https://example.org/remove-test.ics', 'Source remove test', 'active', 'ics_url');
INSERT INTO public.events (city, title, start_time, source, source_uid)
VALUES ('genova', 'Source remove test event', now(), 'Source remove test', 'source-remove-test-event');

INSERT INTO auth.users (id, aud, role, email, encrypted_password, email_confirmed_at)
VALUES
  ('00000000-0000-0000-0000-000000000023', 'authenticated', 'authenticated', 'source-review-user@example.org', '', now()),
  ('00000000-0000-0000-0000-000000000025', 'authenticated', 'authenticated', 'source-review-admin@example.org', '', now())
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.admin_users(user_id)
VALUES ('00000000-0000-0000-0000-000000000025')
ON CONFLICT (user_id) DO NOTHING;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000023', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000023","role":"authenticated"}', true);
SELECT throws_ok(
  $$SELECT * FROM public.remove_feed((SELECT id FROM public.feeds WHERE name = 'Source remove test'))$$,
  '42501',
  'remove_feed: admin access required',
  'authenticated non-admin cannot remove a source'
);
RESET ROLE;
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name = 'Source remove test'), 1,
  'source remains after an unauthorized removal attempt');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000025', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000025","role":"authenticated"}', true);
SELECT results_eq(
  $$SELECT events_deleted, feed_deleted FROM public.remove_feed((SELECT id FROM public.feeds WHERE name = 'Source remove test'))$$,
  $$VALUES (1::bigint, true)$$,
  'authorized admin removes the source and its events atomically'
);
RESET ROLE;
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name = 'Source remove test'), 0,
  'authorized admin removal deletes the source row');
SELECT is((SELECT count(*)::int FROM public.events WHERE source_uid = 'source-remove-test-event'), 0,
  'authorized admin removal deletes source events');

DELETE FROM public.admin_users WHERE user_id = '00000000-0000-0000-0000-000000000025';
DELETE FROM auth.users WHERE id IN (
  '00000000-0000-0000-0000-000000000023',
  '00000000-0000-0000-0000-000000000025'
);

SELECT * FROM finish();
ROLLBACK;
