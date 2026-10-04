-- Public API roles must not directly invoke inherited privileged helpers.
BEGIN;
SELECT plan(4);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM unnest(ARRAY[
      'public.apply_category_override()',
      'public.enforce_category_override()',
      'public.reattach_category_override()',
      'public.refresh_deduplicated_events()',
      'public.refresh_source_names(text)'
    ]) AS f(signature)
    WHERE has_function_privilege('anon', signature::regprocedure, 'EXECUTE')
  ),
  'anon cannot execute inherited trigger or refresh functions'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM unnest(ARRAY[
      'public.apply_category_override()',
      'public.enforce_category_override()',
      'public.reattach_category_override()',
      'public.refresh_deduplicated_events()',
      'public.refresh_source_names(text)'
    ]) AS f(signature)
    WHERE has_function_privilege('authenticated', signature::regprocedure, 'EXECUTE')
  ),
  'authenticated clients cannot execute inherited trigger or refresh functions'
);

SELECT ok(
  has_function_privilege('service_role', 'public.refresh_deduplicated_events()', 'EXECUTE')
  AND has_function_privilege('service_role', 'public.refresh_source_names(text)', 'EXECUTE'),
  'trusted service role can still refresh the public summaries'
);

SELECT ok(
  (
    SELECT count(*) = 7
      AND bool_and('search_path=pg_catalog, public' = ANY(coalesce(p.proconfig, ARRAY[]::text[])))
    FROM pg_proc p
    WHERE p.oid = ANY(ARRAY[
      'public.apply_category_override()'::regprocedure,
      'public.enforce_category_override()'::regprocedure,
      'public.reattach_category_override()'::regprocedure,
      'public.refresh_deduplicated_events()'::regprocedure,
      'public.refresh_source_names(text)'::regprocedure,
      'public.delete_stale_events(text,text[])'::regprocedure,
      'public.validate_scraper_row()'::regprocedure
    ])
  ),
  'every inherited function with unqualified names has a pinned search path'
);

SELECT * FROM finish();
ROLLBACK;
