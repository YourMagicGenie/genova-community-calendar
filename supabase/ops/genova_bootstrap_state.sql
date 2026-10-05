-- Read-only snapshot used by the guarded Genova migration workflow.
-- The workflow runs this file through a direct PostgreSQL connection in read-only mode.
BEGIN READ ONLY;
SELECT jsonb_build_object(
  'migration_versions',
  coalesce(
    (
      SELECT jsonb_agg(m.version::text ORDER BY m.version)
      FROM supabase_migrations.schema_migrations AS m
    ),
    '[]'::jsonb
  ),
  'public_relations',
  coalesce(
    (
      SELECT jsonb_agg(c.relname ORDER BY c.relname)
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
    ),
    '[]'::jsonb
  ),
  'public_tables',
  coalesce(
    (
      SELECT jsonb_agg(c.relname ORDER BY c.relname)
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relkind IN ('r', 'p')
    ),
    '[]'::jsonb
  ),
  'public_rls_tables',
  coalesce(
    (
      SELECT jsonb_agg(c.relname ORDER BY c.relname)
      FROM pg_class AS c
      JOIN pg_namespace AS n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relkind IN ('r', 'p')
        AND c.relrowsecurity
    ),
    '[]'::jsonb
  ),
  'auth_user_count',
  (SELECT count(*)::integer FROM auth.users)
);
COMMIT;
