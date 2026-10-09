BEGIN;
SELECT plan(26);

SELECT has_function('public', 'genova_occurrence_is_current',
  ARRAY['timestamptz','timestamptz','boolean','timestamptz']::text[],
  'the expiration rule is a reusable timezone-aware database function');
SELECT has_function('public', 'list_admin_genova_event_review_queue', ARRAY[]::text[],
  'admin review is served through a database-filtered queue');
SELECT ok(NOT has_function_privilege('anon',
  'public.list_admin_genova_event_review_queue()', 'EXECUTE'),
  'anonymous visitors cannot call the private review queue');
SELECT ok(has_function_privilege('authenticated',
  'public.list_admin_genova_event_review_queue()', 'EXECUTE'),
  'authenticated clients can call the RLS-protected admin queue');
SELECT ok(NOT has_function_privilege('anon',
  'public.genova_occurrence_is_current(timestamptz,timestamptz,boolean,timestamptz)', 'EXECUTE'),
  'anonymous visitors cannot call the internal date helper');

SELECT ok(public.genova_occurrence_is_current(
  '2026-10-09 20:00:00+02', '2026-10-09 22:00:00+02', false, '2026-10-09 21:00:00+02'),
  'a timed event remains current through its end time');
SELECT ok(NOT public.genova_occurrence_is_current(
  '2026-10-09 20:00:00+02', '2026-10-09 22:00:00+02', false, '2026-10-09 22:00:00.000001+02'),
  'a timed event expires after its end time');
SELECT ok(public.genova_occurrence_is_current(
  '2026-10-09 20:00:00+02', '2026-10-09 22:00:00+02', false, '2026-10-09 22:00:00+02'),
  'a timed event remains current at the exact end-time boundary');
SELECT ok(NOT public.genova_occurrence_is_current(
  '2026-10-09 20:00:00+02', NULL, false, '2026-10-09 20:00:00.000001+02'),
  'an event without an end expires after its start');
SELECT ok(public.genova_occurrence_is_current(
  '2026-10-09 20:00:00+02', NULL, false, '2026-10-09 20:00:00+02'),
  'an event without an end remains current at its start-time boundary');
SELECT ok(public.genova_occurrence_is_current(
  '2026-10-25 00:00:00+02', NULL, true, '2026-10-25 23:59:59+01'),
  'an all-day occurrence remains current to the end of its Rome-local date');
SELECT ok(NOT public.genova_occurrence_is_current(
  '2026-10-25 00:00:00+02', NULL, true, '2026-10-25 23:00:00+00'),
  'an all-day occurrence expires at the next Rome-local midnight across the DST change');
SELECT ok(public.genova_occurrence_is_current(
  '2026-10-26 00:00:00+01', NULL, true, '2026-10-25 23:59:00+01'),
  'a future all-day occurrence remains current');
SELECT ok(public.genova_occurrence_is_current(NULL, NULL, false, now()),
  'unknown dates remain eligible for extraction review');

INSERT INTO auth.users (id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
VALUES
  ('00000000-0000-0000-0000-000000001021', 'authenticated', 'authenticated', 'issue102-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000001022', 'authenticated', 'authenticated', 'issue102-user@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now())
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.admin_users (user_id) VALUES ('00000000-0000-0000-0000-000000001021') ON CONFLICT DO NOTHING;

INSERT INTO public.genova_event_facts (
  feed_id, source_uid, title, start_time, end_time, is_all_day, location,
  publisher_label, direct_url, normalized_url, category, review_status
)
SELECT f.id, fixture.source_uid, fixture.title, fixture.start_time, fixture.end_time,
  fixture.is_all_day, 'Test venue', 'Giardini Luzzati',
  fixture.event_url, fixture.event_url,
  'music', fixture.review_status
FROM public.feeds f
CROSS JOIN (VALUES
  ('issue102-expired-review', 'Expired showtime', '2025-02-10 20:00:00+01'::timestamptz, NULL::timestamptz, false, 'needs_review', 'https://www.spazio-comune.org/prodotto/issue102-showtimes/'),
  ('issue102-current-review', 'Upcoming showtime', now() + interval '2 days', NULL::timestamptz, false, 'needs_review', 'https://www.spazio-comune.org/prodotto/issue102-showtimes/'),
  ('issue102-current-all-day', 'Current all-day', date_trunc('day', now() AT TIME ZONE 'Europe/Rome') AT TIME ZONE 'Europe/Rome', NULL::timestamptz, true, 'needs_review', 'https://www.spazio-comune.org/prodotto/issue102-all-day/'),
  ('issue102-unknown-date', 'Unknown date', NULL::timestamptz, NULL::timestamptz, false, 'needs_review', 'https://www.spazio-comune.org/prodotto/issue102-unknown-date/'),
  ('issue102-expired-published', 'Expired published', '2025-02-10 20:00:00+01'::timestamptz, NULL::timestamptz, false, 'validated', 'https://www.spazio-comune.org/prodotto/issue102-expired-published/'),
  ('issue102-current-published', 'Current published', now() + interval '3 days', NULL::timestamptz, false, 'validated', 'https://www.spazio-comune.org/prodotto/issue102-current-published/')
) AS fixture(source_uid, title, start_time, end_time, is_all_day, review_status, event_url)
WHERE f.city = 'genova' AND f.status = 'active'
  AND f.url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';

UPDATE public.genova_event_facts SET category_suggestions =
  '[{"category":"music","confidence":0.86,"evidence":"title keyword match"}]'::jsonb
WHERE source_uid = 'issue102-current-review';

UPDATE public.genova_event_facts SET review_status = 'published'
WHERE source_uid IN ('issue102-expired-published', 'issue102-current-published');

INSERT INTO public.genova_event_fact_audit (event_fact_id, source_uid, old_values, new_values)
SELECT id, source_uid, '{"review_status":"needs_review"}', '{"review_status":"needs_review"}'
FROM public.genova_event_facts WHERE source_uid = 'issue102-expired-review';

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000001022', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000001022","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue()), 0,
  'a signed-in non-admin receives no private queue rows');
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000001021', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000001021","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue()), 4,
  'the admin queue includes current timed, current all-day, unknown-date, and current published events');
SELECT is((SELECT category_suggestions->0->>'category' FROM public.list_admin_genova_event_review_queue()
  WHERE source_uid = 'issue102-current-review'), 'music',
  'the expiration-filtered admin queue returns persisted category suggestions');
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue() WHERE date_state = 'needs_date_extraction'), 1,
  'unknown dates are clearly separated for extraction');
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue() WHERE source_uid = 'issue102-expired-review'), 0,
  'expired events are excluded from active admin review');
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue()
  WHERE direct_url = 'https://www.spazio-comune.org/prodotto/issue102-showtimes/'), 1,
  'the future showtime remains reviewable when another performance of the same listing is past');
SELECT is((SELECT count(*)::int FROM public.list_admin_genova_event_review_queue() WHERE review_status = 'published'), 1,
  'only current published occurrences remain in the admin list');
SELECT is((SELECT count(*)::int FROM public.genova_event_fact_audit WHERE source_uid = 'issue102-expired-review'), 1,
  'filtering leaves expired-event audit history intact');
RESET ROLE;

SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid = 'issue102-expired-review'), 1,
  'filtering preserves the expired source fact');
SELECT is((SELECT count(*)::int FROM public.list_public_genova_events()), 1,
  'the public route hides expired published events and retains current publication');

SELECT is(public.import_genova_luzzati_facts(
  (SELECT id FROM public.feeds WHERE city='genova' AND status='active'
    AND url='https://www.spazio-comune.org/categoria-prodotto/eventi/'),
  jsonb_build_array(jsonb_build_object(
    'feed_id', (SELECT id FROM public.feeds WHERE city='genova' AND status='active'
      AND url='https://www.spazio-comune.org/categoria-prodotto/eventi/'),
    'source_uid', 'genova-luzzati:issue102-expired-import', 'title', 'Old listing',
    'start_time', '2025-02-10T20:00:00+01:00', 'end_time', NULL, 'is_all_day', false,
    'location', 'Test venue', 'publisher', 'Giardini Luzzati',
    'url', 'https://www.spazio-comune.org/prodotto/issue102-expired-import/',
    'normalized_url', 'https://www.spazio-comune.org/prodotto/issue102-expired-import/',
    'review_status', 'needs_review'))
), 0, 'the importer does not persist a past candidate into active review');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid = 'genova-luzzati:issue102-expired-import'), 0,
  'a newly observed expired event is not stored as a new review candidate');

DELETE FROM public.genova_event_fact_audit WHERE source_uid LIKE 'issue102-%';
DELETE FROM public.genova_event_facts WHERE source_uid LIKE 'issue102-%';
DELETE FROM public.admin_users WHERE user_id='00000000-0000-0000-0000-000000001021';
DELETE FROM auth.users WHERE id IN ('00000000-0000-0000-0000-000000001021','00000000-0000-0000-0000-000000001022');
SELECT * FROM finish();
ROLLBACK;
