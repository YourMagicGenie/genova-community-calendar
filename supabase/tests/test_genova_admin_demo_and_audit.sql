BEGIN;
SELECT plan(32);

SELECT has_table('public', 'genova_demo_events', 'fictional events have a separate table');
SELECT has_table('public', 'genova_event_fact_audit', 'event corrections have a private audit table');
SELECT has_function('public', 'list_genova_demo_events', ARRAY[]::text[], 'public demo read is field-limited');
SELECT has_function('public', 'replace_genova_demo_events', ARRAY['jsonb']::text[], 'admin can restore demo events');
SELECT has_function('public', 'clear_genova_demo_events', ARRAY[]::text[], 'admin can clear demo events');
SELECT ok(NOT has_table_privilege('anon', 'public.genova_demo_events', 'SELECT'), 'anonymous users cannot read demo storage directly');
SELECT ok(NOT has_table_privilege('anon', 'public.genova_demo_events', 'DELETE'), 'anonymous users cannot clear demo storage');
SELECT ok(has_function_privilege('anon', 'public.list_genova_demo_events()', 'EXECUTE'), 'anonymous users can read the safe demo route');
SELECT ok(NOT has_function_privilege('anon', 'public.clear_genova_demo_events()', 'EXECUTE'), 'anonymous users cannot clear demos');
SELECT ok(NOT has_function_privilege('anon', 'public.replace_genova_demo_events(jsonb)', 'EXECUTE'), 'anonymous users cannot replace demos');
SELECT ok(NOT has_table_privilege('anon', 'public.genova_event_fact_audit', 'SELECT'), 'anonymous users cannot read correction history');
SELECT ok(has_column_privilege('authenticated', 'public.genova_event_facts', 'normalized_url', 'UPDATE'), 'admins can correct the canonical source link');
SELECT is((SELECT count(*)::int FROM public.list_genova_demo_events()), 24, 'the existing 24 fictional events seed the sample calendar');

INSERT INTO auth.users (id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
VALUES
  ('00000000-0000-0000-0000-000000000086', 'authenticated', 'authenticated', 'issue86-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000000087', 'authenticated', 'authenticated', 'issue86-user@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now())
ON CONFLICT (id) DO NOTHING;
INSERT INTO public.admin_users (user_id) VALUES ('00000000-0000-0000-0000-000000000086') ON CONFLICT DO NOTHING;

SELECT throws_ok($$SELECT public.clear_genova_demo_events()$$, 'admin access required', 'a signed-out caller cannot clear demos');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000087', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000087","role":"authenticated"}', true);
SELECT throws_ok($$SELECT public.clear_genova_demo_events()$$, 'admin access required', 'a signed-in non-admin cannot clear demos');
SELECT is((SELECT count(*)::int FROM public.genova_event_fact_audit), 0, 'a signed-in non-admin cannot read audit entries');
RESET ROLE;

INSERT INTO public.genova_event_facts (feed_id, source_uid, title, publisher_label, direct_url, normalized_url)
SELECT id, 'issue86-admin-audit', 'Needs correction', 'Giardini Luzzati',
  'https://www.spazio-comune.org/prodotto/issue86-admin-audit/',
  'https://www.spazio-comune.org/prodotto/issue86-admin-audit/'
FROM public.feeds WHERE city='genova' AND status='active'
  AND url='https://www.spazio-comune.org/categoria-prodotto/eventi/';

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000086', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000086","role":"authenticated"}', true);
SELECT is(public.clear_genova_demo_events(), 24, 'admin clear removes exactly the demo set');
SELECT is((SELECT count(*)::int FROM public.list_genova_demo_events()), 0, 'public sample route verifies the demo set is empty');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid='issue86-admin-audit'), 1, 'clearing demos leaves real collected facts untouched');
UPDATE public.genova_event_facts SET title='Corrected from the website',
  direct_url='https://www.spazio-comune.org/prodotto/issue86-corrected/',
  normalized_url='https://www.spazio-comune.org/prodotto/issue86-corrected/'
WHERE source_uid='issue86-admin-audit';
SELECT is((SELECT count(*)::int FROM public.genova_event_fact_audit WHERE source_uid='issue86-admin-audit'), 1, 'a correction creates a private audit entry');
SELECT is((SELECT changed_by FROM public.genova_event_fact_audit WHERE source_uid='issue86-admin-audit'), '00000000-0000-0000-0000-000000000086'::uuid, 'audit records the acting admin');
SELECT is((SELECT old_values->>'title' FROM public.genova_event_fact_audit WHERE source_uid='issue86-admin-audit'), 'Needs correction', 'audit records the previous value');
SELECT is((SELECT new_values->>'normalized_url' FROM public.genova_event_fact_audit WHERE source_uid='issue86-admin-audit'), 'https://www.spazio-comune.org/prodotto/issue86-corrected/', 'audit records canonical link corrections');
UPDATE public.genova_event_facts SET start_time=now() + interval '1 day', review_status='validated' WHERE source_uid='issue86-admin-audit';
SELECT throws_ok($$UPDATE public.genova_event_facts SET review_status='published' WHERE source_uid='issue86-admin-audit'$$,
  'published Genova events require title, location, category, and source link', 'incomplete facts cannot be published');
UPDATE public.genova_event_facts SET location='Example venue', category='music' WHERE source_uid='issue86-admin-audit';
UPDATE public.genova_event_facts SET review_status='needs_review' WHERE source_uid='issue86-admin-audit';
SELECT throws_ok($$UPDATE public.genova_event_facts SET review_status='published' WHERE source_uid='issue86-admin-audit'$$,
  'Genova events must be validated before publication', 'needs-review facts cannot skip validation');
UPDATE public.genova_event_facts SET review_status='validated' WHERE source_uid='issue86-admin-audit';
UPDATE public.genova_event_facts SET review_status='published' WHERE source_uid='issue86-admin-audit';
SELECT is((SELECT count(*)::int FROM public.list_public_genova_events() WHERE title='Corrected from the website'), 1, 'complete validated event can be published');
SELECT throws_ok($$UPDATE public.genova_event_facts SET location=NULL WHERE source_uid='issue86-admin-audit'$$,
  'published Genova events require title, location, category, and source link', 'published facts cannot be edited into an incomplete state');
SELECT is(public.replace_genova_demo_events('[{"id":"sample-test-event","title":"Test event","category":"music","daysFromToday":5,"startTime":"19:00","venue":"Example venue, Genova","sourceName":"Example publisher","sourceUrl":"https://example.org/test","tags":[]}]'::jsonb), 1, 'admin can restore one valid fictional event');
SELECT is((SELECT count(*)::int FROM public.list_genova_demo_events()), 1, 'restored event returns through the public demo route');
SELECT throws_ok($$SELECT public.replace_genova_demo_events('[{"id":"sample-bad","title":"Test","category":"music","daysFromToday":5,"startTime":"19:00","venue":"Example","sourceName":"Example","sourceUrl":"https://real-events.it/test","tags":[]}]'::jsonb)$$, 'demo event fields are invalid', 'restore rejects a non-fictional publisher link');
SELECT throws_ok($$SELECT public.replace_genova_demo_events(NULL::jsonb)$$, 'demo events must be an array with at most 100 rows', 'restore rejects a null payload instead of clearing the set');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid='issue86-admin-audit'), 1, 'restoring demos leaves real collected facts untouched');
RESET ROLE;

DELETE FROM public.genova_event_facts WHERE source_uid='issue86-admin-audit';
DELETE FROM public.genova_demo_events WHERE id='sample-test-event';
DELETE FROM public.admin_users WHERE user_id='00000000-0000-0000-0000-000000000086';
DELETE FROM auth.users WHERE id IN ('00000000-0000-0000-0000-000000000086','00000000-0000-0000-0000-000000000087');
SELECT * FROM finish();
ROLLBACK;
