-- Supabase's dashboard can create this SECURITY DEFINER event-trigger helper
-- when automatic RLS is enabled. Keep it callable by PostgreSQL's event trigger
-- mechanism, but not directly through the public Data API.
DO $migration$
DECLARE
  helper_oid oid := to_regprocedure('public.rls_auto_enable()');
  rls_enabled boolean;
BEGIN
  IF helper_oid IS NULL THEN
    RETURN;
  END IF;

  EXECUTE 'REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated';

  IF has_function_privilege('anon', helper_oid, 'EXECUTE')
     OR has_function_privilege('authenticated', helper_oid, 'EXECUTE') THEN
    RAISE EXCEPTION 'rls_auto_enable remains executable by an API role';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_event_trigger
    WHERE evtfoid = helper_oid
      AND evtenabled = 'O'
  ) THEN
    RAISE EXCEPTION 'rls_auto_enable has no enabled event trigger';
  END IF;

  IF to_regclass('public._rls_auto_enable_permission_smoke') IS NOT NULL THEN
    RAISE EXCEPTION 'RLS smoke-test table already exists';
  END IF;

  EXECUTE 'CREATE TABLE public._rls_auto_enable_permission_smoke (id bigint)';
  SELECT relrowsecurity
    INTO rls_enabled
    FROM pg_class
   WHERE oid = to_regclass('public._rls_auto_enable_permission_smoke');

  IF rls_enabled IS DISTINCT FROM TRUE THEN
    RAISE EXCEPTION 'automatic RLS event trigger did not enable RLS on the smoke-test table';
  END IF;

  EXECUTE 'DROP TABLE public._rls_auto_enable_permission_smoke';
END;
$migration$;
