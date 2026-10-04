-- The inherited schema created privileged functions with PostgreSQL's default
-- PUBLIC EXECUTE grant. Trigger functions are not RPC entrypoints, but they
-- do not need direct API execution either. Refresh functions can write data
-- and are called by trusted server-side code only.
REVOKE EXECUTE ON FUNCTION public.apply_category_override()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.enforce_category_override()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.reattach_category_override()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.refresh_deduplicated_events()
  FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.refresh_source_names(text)
  FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.refresh_deduplicated_events()
  TO service_role;
GRANT EXECUTE ON FUNCTION public.refresh_source_names(text)
  TO service_role;

-- Pin the inherited functions' name resolution. The public schema does not
-- grant CREATE to anon or authenticated; pg_catalog takes precedence.
-- Their existing unqualified table references continue to resolve in public.
ALTER FUNCTION public.apply_category_override()
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.enforce_category_override()
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.reattach_category_override()
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.refresh_deduplicated_events()
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.refresh_source_names(text)
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.delete_stale_events(text, text[])
  SET search_path TO pg_catalog, public;
ALTER FUNCTION public.validate_scraper_row()
  SET search_path TO pg_catalog, public;
