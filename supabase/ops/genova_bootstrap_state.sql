-- Read-only snapshot used by the one-time, guarded Genova bootstrap workflow.
SELECT
  coalesce(
    (
      SELECT json_agg(m.version::text ORDER BY m.version)
      FROM supabase_migrations.schema_migrations AS m
    ),
    '[]'::json
  ) AS migration_versions,
  coalesce(
    (
      SELECT json_agg(c.relname ORDER BY c.relname)
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
    ),
    '[]'::json
  ) AS public_tables,
  coalesce(
    (
      SELECT json_agg(c.relname ORDER BY c.relname)
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relkind IN ('r', 'p')
        AND c.relrowsecurity
    ),
    '[]'::json
  ) AS public_rls_tables,
  (SELECT count(*)::integer FROM auth.users) AS auth_user_count;
