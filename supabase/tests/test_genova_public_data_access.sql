-- Genova API access must not expose the inherited all-events or curator views.
BEGIN;
SELECT plan(18);

SELECT ok(
  NOT has_table_privilege('anon', 'public.deduplicated_events', 'SELECT')
  AND NOT has_table_privilege('authenticated', 'public.deduplicated_events', 'SELECT'),
  'browser roles cannot read the inherited materialized view with private fields'
);

SELECT ok(
  NOT has_table_privilege('anon', 'public.category_overrides_view', 'SELECT')
  AND NOT has_table_privilege('authenticated', 'public.category_overrides_view', 'SELECT'),
  'browser roles cannot read curator metadata through the legacy view'
);

SELECT ok(
  NOT has_table_privilege('anon', 'public.distinct_cities', 'SELECT')
  AND NOT has_table_privilege('authenticated', 'public.distinct_cities', 'SELECT'),
  'browser roles cannot read the inherited city directory'
);

SELECT ok(
  NOT has_table_privilege('anon', 'public.events', 'SELECT')
  AND NOT has_table_privilege('authenticated', 'public.events', 'SELECT'),
  'browser roles cannot query raw event records directly'
);

SELECT ok(
  NOT has_function_privilege('anon', 'public.get_curator_name(uuid)', 'EXECUTE')
  AND NOT has_function_privilege('authenticated', 'public.get_curator_name(uuid)', 'EXECUTE'),
  'browser roles cannot look up another curator by UUID'
);

SELECT ok(
  has_function_privilege('service_role', 'public.get_curator_name(uuid)', 'EXECUTE'),
  'trusted server code retains the curator lookup needed by private maintenance'
);

SELECT ok(
  NOT has_function_privilege('anon', 'public.get_my_github_username()', 'EXECUTE')
  AND has_function_privilege('authenticated', 'public.get_my_github_username()', 'EXECUTE'),
  'GitHub identity helper is limited to signed-in sessions for its own RLS check'
);

SELECT ok(
  NOT has_function_privilege('anon', 'public.get_my_google_email()', 'EXECUTE')
  AND has_function_privilege('authenticated', 'public.get_my_google_email()', 'EXECUTE'),
  'Google identity helper is limited to signed-in sessions for its own RLS check'
);

SELECT ok(
  has_function_privilege('service_role', 'public.refresh_deduplicated_events()', 'EXECUTE')
  AND has_function_privilege('service_role', 'public.refresh_source_names(text)', 'EXECUTE'),
  'trusted server-side refresh operations remain available'
);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND NOT EXISTS (
        SELECT 1 FROM unnest(coalesce(p.proconfig, ARRAY[]::text[])) AS setting
        WHERE setting LIKE 'search_path=%'
      )
  ),
  'every SECURITY DEFINER function in public has a pinned search path'
);

SELECT ok(
  (SELECT extnamespace = 'extensions'::regnamespace
   FROM pg_extension WHERE extname = 'pg_net'),
  'pg_net is installed in the non-API extensions schema'
);

SELECT ok(
  has_function_privilege('authenticated', 'public.remove_feed(bigint)', 'EXECUTE'),
  'authenticated admin workflow retains access to guarded remove_feed'
);

SELECT ok(
  (SELECT count(*) = 0 FROM cron.job),
  'no inherited scheduled collection jobs are active'
);

SELECT ok(
  NOT has_table_privilege('anon', 'public.feed_source_reviews', 'SELECT')
  AND NOT has_table_privilege('anon', 'public.agent_runs', 'SELECT'),
  'anonymous visitors cannot read private source review or run history'
);

SELECT ok(
  (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.feed_source_reviews'::regclass),
  'source review table enforces row-level security'
);

SELECT ok(
  NOT has_table_privilege('anon', 'public.admin_users', 'SELECT'),
  'anonymous visitors cannot read the admin allowlist'
);

SELECT ok(
  NOT has_table_privilege('authenticated', 'public.agent_runs', 'INSERT')
  AND NOT has_table_privilege('authenticated', 'public.agent_runs', 'UPDATE')
  AND NOT has_table_privilege('authenticated', 'public.agent_runs', 'DELETE'),
  'browser clients cannot write private run history'
);

SELECT ok(
  (SELECT count(*) = 0 FROM public.events)
  AND (SELECT count(*) = 0 FROM public.agent_runs),
  'security migration preserves the empty pre-pilot data state'
);

SELECT * FROM finish();
ROLLBACK;
