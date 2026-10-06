BEGIN;
SELECT plan(31);

SELECT has_column('public', 'feeds', 'request_cadence_minutes', 'source request cadence is recorded');
SELECT has_column('public', 'feeds', 'daily_request_cap', 'source daily request cap is recorded');
SELECT has_column('public', 'feeds', 'last_attempt_at', 'source last attempt is recorded');
SELECT has_column('public', 'feeds', 'last_success_at', 'source last success is recorded');
SELECT has_column('public', 'feeds', 'last_result', 'source last result is recorded');

SELECT results_eq(
  $$ SELECT count(*)::bigint FROM public.feeds
     WHERE city='genova'
       AND url='https://www.spazio-comune.org/categoria-prodotto/eventi/'
       AND status='active'
       AND feed_type='web_index'
       AND request_cadence_minutes=1440
       AND daily_request_cap=1 $$,
  ARRAY[1::bigint],
  'the owner-selected Luzzati index is the one active bounded source'
);

SELECT results_eq(
  $$ SELECT count(*)::bigint FROM public.feed_source_reviews
     WHERE city='genova'
       AND feed_url='https://www.spazio-comune.org/categoria-prodotto/eventi/'
       AND genova_fit='confirmed'
       AND access_notes IS NOT NULL $$,
  ARRAY[1::bigint],
  'Luzzati source review retains access provenance privately'
);

SELECT has_table('public', 'genova_event_candidates', 'private Genova event candidate table exists');
SELECT has_column('public', 'genova_event_candidates', 'feed_id', 'candidate source ID is retained');
SELECT has_column('public', 'genova_event_candidates', 'normalized_url', 'candidate normalized URL is retained');
SELECT has_column('public', 'genova_event_candidates', 'category_confidence', 'candidate category confidence is reviewable');
SELECT has_column('public', 'genova_event_candidates', 'review_status', 'candidate publication review state is separate');
SELECT has_column('public', 'genova_event_candidates', 'first_seen', 'candidate first-seen time is retained');
SELECT has_column('public', 'genova_event_candidates', 'last_seen', 'candidate last-seen time is retained');
SELECT col_is_null('public', 'genova_event_candidates', 'start_time', 'unknown start times remain nullable');
SELECT col_is_null('public', 'genova_event_candidates', 'location', 'unknown locations remain nullable');

SELECT has_table('public', 'genova_source_scans', 'private Genova source scan table exists');
SELECT has_column('public', 'genova_source_scans', 'collector_revision', 'scan collector revision is retained');
SELECT has_column('public', 'genova_source_scans', 'robots_decision', 'scan robots decision is retained');
SELECT has_column('public', 'genova_source_scans', 'request_count', 'scan request count is retained');
SELECT has_column('public', 'genova_source_scans', 'error_summary', 'scan safe error summary is retained');

SELECT has_table('public', 'genova_public_events', 'field-limited Genova public table exists');
SELECT has_column('public', 'genova_public_events', 'title', 'public event title is exposed');
SELECT has_column('public', 'genova_public_events', 'start_time', 'public event start is exposed');
SELECT has_column('public', 'genova_public_events', 'location', 'public event location is exposed');
SELECT has_column('public', 'genova_public_events', 'publisher', 'public event publisher is exposed');
SELECT has_column('public', 'genova_public_events', 'event_url', 'public event source link is exposed');
SELECT has_column('public', 'genova_public_events', 'category', 'public event category is exposed');

SELECT results_eq(
  $$ SELECT count(*)::bigint
     FROM information_schema.columns
     WHERE table_schema='public' AND table_name='genova_public_events'
       AND column_name IN ('description','image_url','transcript','source_uid','category_confidence','review_status') $$,
  ARRAY[0::bigint],
  'public Genova table contains no descriptions, images, transcripts, source identity, confidence, or review state'
);

SELECT ok(
  has_table_privilege('anon', 'public.genova_public_events', 'SELECT')
  AND NOT has_table_privilege('anon', 'public.genova_event_candidates', 'SELECT')
  AND NOT has_table_privilege('anon', 'public.genova_source_scans', 'SELECT'),
  'anonymous visitors can read only the field-limited publication table'
);

SELECT ok(
  has_table_privilege('service_role', 'public.genova_event_candidates', 'INSERT')
  AND has_table_privilege('service_role', 'public.genova_source_scans', 'INSERT'),
  'trusted collection code can persist candidates and scan provenance'
);

SELECT * FROM finish();
ROLLBACK;
