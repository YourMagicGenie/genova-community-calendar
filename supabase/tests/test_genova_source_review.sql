-- Candidate metadata stays out of public reads; only a trusted admin can
-- inspect candidates and change their review state.
BEGIN;
SELECT plan(20);

SELECT has_column('public', 'feeds', 'publisher_url', 'publisher URL is retained');
SELECT has_column('public', 'feeds', 'discovery_method', 'collection/discovery method is recorded');
SELECT has_column('public', 'feed_source_reviews', 'source_provenance', 'candidate provenance is retained');
SELECT has_column('public', 'feed_source_reviews', 'access_notes', 'source access notes are retained');
SELECT has_column('public', 'feed_source_reviews', 'genova_fit', 'Genova fit is reviewable');
SELECT has_column('public', 'feed_source_reviews', 'discovery_reason', 'discovery reason is retained');
SELECT has_column('public', 'feed_source_reviews', 'reviewed_at', 'review time is recorded');
SELECT has_column('public', 'feed_source_reviews', 'reviewed_by', 'reviewing admin is recorded');

INSERT INTO public.feeds (
  city, url, name, status, feed_type, publisher_url, discovery_method
) VALUES
  ('genova', 'https://example.org/active.ics', 'Source review active', 'active', 'ics_url',
   'https://example.org', 'ics'),
  ('genova', 'https://example.org/pending.ics', 'Source review pending', 'pending', 'ics_url',
   'https://example.org', 'manual');

INSERT INTO public.feed_source_reviews (
  city, feed_url, source_provenance, access_notes, genova_fit, discovery_reason
) VALUES
  ('genova', 'https://example.org/active.ics', 'fixture test', 'public page', 'confirmed', 'event listing'),
  ('genova', 'https://example.org/pending.ics', 'fixture test', 'access not yet checked', 'unknown', 'submitted candidate');

-- Neither anonymous visitors nor signed-in non-admin users can enumerate
-- pending candidates or their review notes.
SET LOCAL ROLE anon;
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name LIKE 'Source review %'), 1,
  'anonymous readers see only the active source');
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name = 'Source review pending'), 0,
  'anonymous readers cannot see pending candidates');
SELECT ok(NOT has_table_privilege('anon', 'public.feed_source_reviews', 'SELECT'),
  'anonymous role has no grant on the private review table');
RESET ROLE;

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('00000000-0000-0000-0000-000000000013', 'authenticated', 'authenticated',
   'genova-non-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now()),
  ('00000000-0000-0000-0000-000000000015', 'authenticated', 'authenticated',
   'genova-admin@example.org', '', now(), '{"provider":"email","providers":["email"]}', '{}', now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.admin_users(user_id)
VALUES ('00000000-0000-0000-0000-000000000015')
ON CONFLICT (user_id) DO NOTHING;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000013', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000013","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name = 'Source review pending'), 0,
  'authenticated non-admin cannot see pending candidates');
SELECT is((SELECT count(*)::int FROM public.feed_source_reviews), 0,
  'authenticated non-admin cannot see review notes');
UPDATE public.feeds SET status = 'active'
WHERE name = 'Source review pending';
RESET ROLE;
SELECT is((SELECT status FROM public.feeds WHERE name = 'Source review pending'), 'pending',
  'authenticated non-admin cannot approve a candidate');

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000015', true);
SELECT set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-000000000015","role":"authenticated"}', true);
SELECT is((SELECT count(*)::int FROM public.feeds WHERE name = 'Source review pending'), 1,
  'authorized admin can review pending candidates');
SELECT is((SELECT count(*)::int FROM public.feed_source_reviews), 2,
  'authorized admin can inspect all review notes');
UPDATE public.feeds
SET status = 'paused'
WHERE name = 'Source review pending';
UPDATE public.feed_source_reviews
SET reviewed_at = now(), reviewed_by = auth.uid()
WHERE city = 'genova' AND feed_url = 'https://example.org/pending.ics';
SELECT is((SELECT status FROM public.feeds WHERE name = 'Source review pending'), 'paused',
  'authorized admin can pause a source');
SELECT is((SELECT count(*)::int FROM public.feeds WHERE status = 'active' AND name LIKE 'Source review %'), 1,
  'paused source is excluded from active collection');
UPDATE public.feeds
SET status = 'rejected'
WHERE name = 'Source review pending';
SELECT is((SELECT status FROM public.feeds WHERE name = 'Source review pending'), 'rejected',
  'authorized admin can reject a candidate');
UPDATE public.feed_source_reviews
SET reviewed_at = now(), reviewed_by = auth.uid()
WHERE city = 'genova' AND feed_url = 'https://example.org/pending.ics';
SELECT is((SELECT reviewed_by FROM public.feed_source_reviews WHERE feed_url = 'https://example.org/pending.ics'), auth.uid(),
  'admin review records the acting user');

RESET ROLE;
DELETE FROM public.feeds WHERE name LIKE 'Source review %';
DELETE FROM public.admin_users WHERE user_id = '00000000-0000-0000-0000-000000000015';
DELETE FROM auth.users WHERE id IN (
  '00000000-0000-0000-0000-000000000013',
  '00000000-0000-0000-0000-000000000015'
);

SELECT * FROM finish();
ROLLBACK;
