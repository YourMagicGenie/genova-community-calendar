 may install this helper when automatic RLS is enabled.
-- Local projects without that dashboard-created helper remain supported.
BEGIN;
SELECT plan(2);

SELECT ok(
  CASE
    WHEN to_regprocedure('public.rls_auto_enable()') IS NULL THEN TRUE
    ELSE NOT has_function_privilege('anon', to_regprocedure('public.rls_auto_enable()'), 'EXECUTE')
      AND NOT has_function_privilege('authenticated', to_regprocedure('public.rls_auto_enable()'), 'EXECUTE')
  END,
  'the automatic RLS helper is not executable by API roles when present'
);

SELECT ok(
  CASE
    WHEN to_regprocedure('public.rls_auto_enable()') IS NULL THEN TRUE
    ELSE EXISTS (
      SELECT 1
      FROM pg_event_trigger
      WHERE evtfoid = to_regprocedure('public.rls_auto_enable()')
        AND evtenabled = 'O'
    )
  END,
  'the automatic RLS event trigger remains enabled when the helper is present'
);

SELECT * FROM finish();
ROLLBACK;
