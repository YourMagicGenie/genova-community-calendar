-- The stale-event RPC is SECURITY DEFINER and must never be publicly callable.
BEGIN;
SELECT plan(3);

SELECT ok(
  NOT has_function_privilege('anon', 'public.delete_stale_events(text,text[])', 'EXECUTE'),
  'anon cannot execute delete_stale_events'
);
SELECT ok(
  NOT has_function_privilege('authenticated', 'public.delete_stale_events(text,text[])', 'EXECUTE'),
  'authenticated users cannot execute delete_stale_events'
);
SELECT ok(
  has_function_privilege('service_role', 'public.delete_stale_events(text,text[])', 'EXECUTE'),
  'service_role can execute delete_stale_events'
);

SELECT * FROM finish();
ROLLBACK;
