BEGIN;
SELECT plan(22);

SELECT has_column('public', 'genova_event_facts', 'source_metadata', 'private bulletin provenance has a bounded storage column');
SELECT has_function('public', 'import_genova_bulletin_facts', ARRAY['bigint','text','text','timestamp with time zone','text','jsonb'], 'bulletin importer is installed');
SELECT ok(NOT has_function_privilege('anon', 'public.import_genova_bulletin_facts(bigint,text,text,timestamptz,text,jsonb)', 'EXECUTE'), 'anonymous visitors cannot import bulletin facts');
SELECT ok(NOT has_function_privilege('authenticated', 'public.import_genova_bulletin_facts(bigint,text,text,timestamptz,text,jsonb)', 'EXECUTE'), 'browser users cannot import bulletin facts');
SELECT ok(has_function_privilege('service_role', 'public.import_genova_bulletin_facts(bigint,text,text,timestamptz,text,jsonb)', 'EXECUTE'), 'only the trusted service role can import bulletin facts');
SELECT ok(NOT has_table_privilege('anon', 'public.genova_event_facts', 'SELECT'), 'anonymous visitors cannot read private facts or evidence');

INSERT INTO public.feeds (city, url, name, status, feed_type)
VALUES
  ('genova', 'https://bulletin-fixture.example.org/events/', 'Fixture Bulletin Publisher', 'active', 'web_index'),
  ('genova', 'https://pending-fixture.example.org/events/', 'Pending Fixture Publisher', 'pending', 'web_index')
ON CONFLICT (city, url) DO UPDATE SET status = EXCLUDED.status, name = EXCLUDED.name;

CREATE FUNCTION pg_temp.bulletin_event(uid text, title text, start_value text, page integer DEFAULT 1)
RETURNS jsonb LANGUAGE sql AS $$
  SELECT jsonb_build_object(
    'source_uid', 'genova-bulletin:' || uid,
    'title', title,
    'start_time', start_value,
    'end_time', NULL,
    'normalized_url', 'https://bulletin-fixture.example.org/files/october.pdf',
    'location', 'Example Hall',
    'category_suggestions', jsonb_build_array(jsonb_build_object(
      'category', 'music', 'confidence', 0.8, 'evidence', 'section heading match')),
    'field_evidence', jsonb_build_object('date', jsonb_build_object('page', page, 'text', '12 gennaio 2099')),
    'unresolved_reasons', '[]'::jsonb,
    'date_precision', 'day',
    'source_page', page,
    'source_bbox', '[10,20,100,40]'::jsonb,
    'evidence_note', 'Monthly bulletin PDF · page ' || page,
    'partial_dates', '[]'::jsonb,
    'start_date_candidate', '2099-01-12',
    'end_date_candidate', NULL
  );
$$;
CREATE FUNCTION pg_temp.import_fixture(events jsonb, feed_url text DEFAULT 'https://bulletin-fixture.example.org/events/')
RETURNS integer LANGUAGE sql AS $$
  SELECT public.import_genova_bulletin_facts(
    f.id, feed_url, 'https://bulletin-fixture.example.org/files/october.pdf',
    '2098-12-01T12:00:00Z'::timestamptz, '1.0.0', events
  ) FROM public.feeds f WHERE f.city = 'genova' AND f.url = feed_url;
$$;

SELECT throws_ok(
  $$SELECT pg_temp.import_fixture(jsonb_build_array(pg_temp.bulletin_event('pending', 'Pending', '2099-01-12T18:00:00+01:00')), 'https://pending-fixture.example.org/events/')$$,
  'bulletin import requires the matching active Genova source',
  'pending source state blocks persistence'
);

SELECT is(
  pg_temp.import_fixture(jsonb_build_array(
    pg_temp.bulletin_event(repeat('a', 64), 'Same-time performance one', '2099-01-12T18:00:00+01:00', 1),
    pg_temp.bulletin_event(repeat('b', 64), 'Same-time performance two', '2099-01-12T18:00:00+01:00', 1)
  )),
  2,
  'two separate listings from one bulletin can share its URL and time'
);
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid LIKE 'genova-bulletin:%'), 2, 'both separate listings are stored');
SELECT is((SELECT count(DISTINCT source_uid)::int FROM public.genova_event_facts WHERE source_uid LIKE 'genova-bulletin:%'), 2, 'candidate identity keeps the same-time listings distinct');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid LIKE 'genova-bulletin:%' AND review_status = 'needs_review'), 2, 'import never advances review status');
SELECT is((SELECT count(*)::int FROM public.list_public_genova_events() WHERE title LIKE 'Same-time performance%'), 0, 'unreviewed bulletin facts stay out of public events');
SELECT is((SELECT source_metadata ->> 'kind' FROM public.genova_event_facts WHERE source_uid = 'genova-bulletin:' || repeat('a', 64)), 'monthly_bulletin_pdf', 'source metadata marks the PDF method');
SELECT is((SELECT source_metadata #>> '{field_evidence,date,text}' FROM public.genova_event_facts WHERE source_uid = 'genova-bulletin:' || repeat('a', 64)), '12 gennaio 2099', 'field evidence is retained for review');
SELECT is((SELECT source_metadata ->> 'parser_version' FROM public.genova_event_facts WHERE source_uid = 'genova-bulletin:' || repeat('a', 64)), '1.0.0', 'parser version is retained');

SELECT is(
  pg_temp.import_fixture(jsonb_build_array(
    pg_temp.bulletin_event(repeat('a', 64), 'Same-time performance one updated', '2099-01-12T18:00:00+01:00', 1),
    pg_temp.bulletin_event(repeat('b', 64), 'Same-time performance two', '2099-01-12T18:00:00+01:00', 1)
  )),
  2,
  'reimport updates the two existing source identities'
);
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid LIKE 'genova-bulletin:%'), 2, 'reimport creates no duplicates');
SELECT is((SELECT title FROM public.genova_event_facts WHERE source_uid = 'genova-bulletin:' || repeat('a', 64)), 'Same-time performance one updated', 'unreviewed source facts can be refreshed');

SELECT throws_ok(
  $$SELECT public.import_genova_bulletin_facts(
      (SELECT id FROM public.feeds WHERE city='genova' AND url='https://bulletin-fixture.example.org/events/'),
      'https://wrong.example.org/events/', 'https://bulletin-fixture.example.org/files/october.pdf',
      now(), '1.0.0', jsonb_build_array(pg_temp.bulletin_event('mismatch', 'Mismatch', '2099-01-12T18:00:00+01:00'))
    )$$,
  'bulletin import requires the matching active Genova source',
  'a different source page cannot use this active feed ID'
);
SELECT throws_ok(
  $$SELECT pg_temp.import_fixture(jsonb_build_array(pg_temp.bulletin_event('malformed', 'Bad evidence', '2099-01-12T18:00:00+01:00') || jsonb_build_object('field_evidence', 'not an object')))$$,
  'bulletin event facts do not match the bounded review contract',
  'malformed field evidence is rejected'
);
SELECT throws_ok(
  $$SELECT pg_temp.import_fixture(jsonb_build_array(pg_temp.bulletin_event('same', 'First duplicate', '2099-01-12T18:00:00+01:00'), pg_temp.bulletin_event('same', 'Duplicate identity', '2099-01-12T18:00:00+01:00')))$$,
  'bulletin payload contains duplicate candidate identities',
  'duplicate identities in one payload are rejected'
);
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE source_uid = 'genova-bulletin:malformed'), 0, 'rejected inputs write no partial rows');

DELETE FROM public.genova_event_facts WHERE source_uid LIKE 'genova-bulletin:%';
DELETE FROM public.feeds WHERE city = 'genova' AND url IN (
  'https://bulletin-fixture.example.org/events/', 'https://pending-fixture.example.org/events/'
);
SELECT * FROM finish();
ROLLBACK;
