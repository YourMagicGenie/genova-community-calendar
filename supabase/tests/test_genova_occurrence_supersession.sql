BEGIN;
SELECT plan(21);
CREATE FUNCTION pg_temp.fact(uid text, slug text, starts text DEFAULT NULL, label text DEFAULT 'Fixture')
RETURNS jsonb LANGUAGE sql AS $$
 SELECT jsonb_build_object('feed_id', id, 'source_uid', 'genova-luzzati:' || uid,
   'title', label, 'start_time', starts, 'publisher', 'Giardini Luzzati',
   'url', 'https://www.spazio-comune.org/prodotto/' || slug || '/',
   'normalized_url', 'https://www.spazio-comune.org/prodotto/' || slug || '/',
   'review_status', 'needs_review', 'evidence_note', 'fixture_source_facts')
 FROM public.feeds WHERE url='https://www.spazio-comune.org/categoria-prodotto/eventi/' AND city='genova';
$$;
CREATE FUNCTION pg_temp.import_facts(events jsonb) RETURNS integer LANGUAGE sql AS $$
 SELECT public.import_genova_luzzati_facts(id, events) FROM public.feeds
 WHERE url='https://www.spazio-comune.org/categoria-prodotto/eventi/' AND city='genova';
$$;
SELECT has_column('public','genova_event_facts','superseded_by','audit relationship exists');
SELECT ok(NOT has_function_privilege('anon','public.import_genova_luzzati_facts(bigint,jsonb)','EXECUTE'),'anon cannot import');
SELECT ok(NOT has_function_privilege('authenticated','public.reconcile_genova_event_placeholders(bigint,text[])','EXECUTE'),'browser cannot supersede records');
SELECT ok(NOT has_column_privilege('authenticated','public.genova_event_facts','superseded_by','UPDATE'),'browser cannot forge audit relationship');
SELECT ok(has_column_privilege('authenticated','public.genova_event_facts','review_status','UPDATE'),'admin review update grant remains');

SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('single-u','single')));
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('single-d','single','2026-10-12T18:00:00+02:00')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/single/'),2,'enrichment retains both audit records');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/single/' AND superseded_by IS NULL),1,'review queue has one active occurrence');
SELECT ok((SELECT old.superseded_by = new.id FROM public.genova_event_facts old, public.genova_event_facts new WHERE old.source_uid='genova-luzzati:single-u' AND new.source_uid='genova-luzzati:single-d'),'placeholder links to the dated occurrence');
SELECT is((SELECT review_status FROM public.genova_event_facts WHERE source_uid='genova-luzzati:single-u'),'needs_review','supersession does not invent a human rejection');
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('single-d','single','2026-10-12T18:00:00+02:00')));
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('single-u','single')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/single/'),2,'repeated and dated-to-partial scans add no stale variant');
SELECT is((SELECT start_time::text FROM public.genova_event_facts WHERE source_uid='genova-luzzati:single-d'), '2026-10-12 16:00:00+00','dated-to-partial does not clear the reliable time');

SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('series-u','series')));
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('series-a','series','2026-10-12T18:00:00+02:00'), pg_temp.fact('series-b','series','2026-10-13T18:00:00+02:00')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/series/' AND superseded_by IS NULL),3,'one URL with two dates remains distinct and flagged for review');
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('series-u','series')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/series/'),3,'partial scan does not add variants to a shared-URL series');

SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('protected-u','protected')));
UPDATE public.genova_event_facts SET review_status='validated', title='Human correction' WHERE source_uid='genova-luzzati:protected-u';
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('protected-d','protected','2026-10-12T18:00:00+02:00','Human correction')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/protected/' AND superseded_by IS NULL),2,'reviewed undated identity requires human reconciliation');
UPDATE public.genova_event_facts SET review_status='validated', title='Published correction', location='Curated venue', category='community-social' WHERE source_uid='genova-luzzati:protected-d';
UPDATE public.genova_event_facts SET review_status='published' WHERE source_uid='genova-luzzati:protected-d';
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('protected-d','protected','2026-10-12T18:00:00+02:00','Publisher change')));
SELECT is((SELECT title FROM public.genova_event_facts WHERE source_uid='genova-luzzati:protected-d'),'Published correction','collector does not overwrite a reviewed title');
SELECT is((SELECT location FROM public.genova_event_facts WHERE source_uid='genova-luzzati:protected-d'),'Curated venue','collector preserves curated fields');
SELECT is((SELECT review_status FROM public.genova_event_facts WHERE source_uid='genova-luzzati:protected-d'),'published','collector preserves publication state');
SELECT throws_ok($$UPDATE public.genova_event_facts SET start_time=NULL WHERE source_uid='genova-luzzati:single-d'$$,'a supersession target must retain its known start time','cannot invalidate an audit link');
SELECT throws_ok($$UPDATE public.genova_event_facts SET superseded_by=(SELECT id FROM public.genova_event_facts WHERE source_uid='genova-luzzati:single-d'), superseded_at=now() WHERE source_uid='genova-luzzati:series-u'$$,'supersession requires a dated occurrence of the same source URL','cross-URL supersession fails closed');
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('different-u','different',NULL,'Old title')));
SELECT pg_temp.import_facts(jsonb_build_array(pg_temp.fact('different-d','different','2026-10-12T18:00:00+02:00','New title')));
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE normalized_url LIKE '%/different/' AND superseded_by IS NULL),2,'different titles remain ambiguous rather than silently matched');
SELECT is((SELECT count(*)::int FROM public.genova_event_facts WHERE superseded_by IS NOT NULL AND review_status='published'),0,'audit placeholders are never public');
SELECT * FROM finish();
ROLLBACK;
