BEGIN;
SELECT plan(24);

SELECT has_table('public', 'genova_event_facts', 'reviewable Genova event facts table exists');
SELECT has_table('public', 'genova_source_scans', 'private source scan provenance table exists');
SELECT has_function('public', 'list_public_genova_events', ARRAY[]::text[], 'field-limited public event function exists');
SELECT has_column('public', 'genova_event_facts', 'review_status', 'event facts have review state');
SELECT has_column('public', 'genova_event_facts', 'normalized_url', 'event facts retain normalized URL');
SELECT has_column('public', 'genova_event_facts', 'first_seen', 'event facts retain first-seen time');
SELECT has_column('public', 'genova_event_facts', 'last_seen', 'event facts retain last-seen time');
SELECT has_column('public', 'genova_source_scans', 'request_count', 'scan provenance records request count');

SELECT is(
  (SELECT feed_type FROM public.feeds
   WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/'),
  'web_index',
  'Luzzati is registered in the existing feeds registry as the web index source'
);
SELECT is(
  (SELECT status FROM public.feeds
   WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/'),
  'active',
  'owner-selected Luzzati source is active'
);
SELECT is(
  (SELECT genova_fit FROM public.feed_source_reviews
   WHERE city = 'genova' AND feed_url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/'),
  'confirmed',
  'Luzzati source review records confirmed Genova fit'
);

SELECT ok(NOT has_table_privilege('anon', 'public.genova_event_facts', 'SELECT'),
  'anonymous visitors cannot read the review table directly');
SELECT ok(NOT has_table_privilege('anon', 'public.genova_source_scans', 'SELECT'),
  'anonymous visitors cannot read scan history');
SELECT ok(has_function_privilege('anon', 'public.list_public_genova_events()', 'EXECUTE'),
  'anonymous visitors can call the field-limited public route');

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('00000000-0000-0000-0000-000000000051', 'authenticated', 'authenticated',
   'issue51-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000000052', 'authenticated', 'authenticated',
   'issue51-user@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.admin_users(user_id)
VALUES ('00000000-0000-0000-0000-000000000051')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO public.genova_event_facts (
  feed_id, source_uid, title, start_time, location, publisher_label,
  direct_url, normalized_url, review_status
)
SELECT id, 'issue51-published', 'Published fixture',
       '2026-10-07T19:00:00+02:00', 'Giardini Luzzati - Spazio Comune',
       'Giardini Luzzati / Spazio Comune',
       'https://www.spazio-comune.org/prodotto/published-fixture/',
       'https://www.spazio-comune.org/prodotto/published-fixture/',
       'published'
FROM public.feeds
WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';

INSERT INTO public.genova_event_facts (
  feed_id, source_uid, title, start_time, publisher_label,
  direct_url, normalized_url, review_status
)
SELECT id, 'issue51-review', 'Needs review fixture',
       NULL, 'Giardini Luzzati / Spazio Comune',
       'https://www.spazio-comune.org/prodotto/review-fixture/',
       'https://www.spazio-comune.org/prodotto/review-fixture/',
       'needs_review'
FROM public.feeds
WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';

SELECT is((SELECT count(*)::int FROM public.list_public_genova_events()), 1,
  'public route returns only the published validated fixture');
SELECT is((SELECT title FROM public.list_public_genova_events()), 'Published fixture',
  'public route exposes the published event title');
SELECT is((SELECT publisher FROM public.list_public_genova_events()), 'Giardini Luzzati / Spazio Comune',
  'public route exposes publisher attribution');

SET LOCAL ROLE anon;
SELECT is((SELECT count(*)::int FROM public.list_public_genova_events()), 1,
  'anonymous visitor can read the published event route');
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000052', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000052","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.genova_event_facts), 0,
  'signed-in non-admin cannot inspect reviewable event facts');
SELECT is((SELECT count(*)::int FROM public.genova_source_scans), 0,
  'signed-in non-admin cannot inspect private scan history');
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000051', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000051","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.genova_event_facts), 2,
  'registered admin can inspect all event facts');
UPDATE public.genova_event_facts
SET review_status = 'validated'
WHERE source_uid = 'issue51-review';
SELECT is((SELECT review_status FROM public.genova_event_facts WHERE source_uid = 'issue51-review'), 'validated',
  'registered admin can advance review state');
RESET ROLE;

SELECT throws_ok(
  $$
    UPDATE public.genova_event_facts
    SET review_status = 'published'
    WHERE source_uid = 'issue51-review'
  $$,
  'published Genova events require a start time',
  'unknown-time facts cannot be published'
);

UPDATE public.feeds
SET status = 'paused'
WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';

SELECT is((SELECT count(*)::int FROM public.list_public_genova_events()), 0,
  'pausing a source immediately removes its events from the public route');

UPDATE public.feeds
SET status = 'active'
WHERE city = 'genova' AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';

SELECT is((SELECT count(*)::int FROM public.list_public_genova_events()), 1,
  'reactivating the approved source restores its published event');

DELETE FROM public.genova_event_facts WHERE source_uid IN ('issue51-published', 'issue51-review');
DELETE FROM public.admin_users WHERE user_id = '00000000-0000-0000-0000-000000000051';
DELETE FROM auth.users WHERE id IN (
  '00000000-0000-0000-0000-000000000051',
  '00000000-0000-0000-0000-000000000052'
);

SELECT * FROM finish();
ROLLBACK;
