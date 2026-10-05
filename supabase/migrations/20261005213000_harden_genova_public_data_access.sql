-- Close API access to inherited materialized views that contain unreviewed
-- event fields and curator metadata. The Genova sample page currently uses
-- fictional data; Issue #51 will add a published, field-limited read path.
REVOKE SELECT ON TABLE public.deduplicated_events FROM PUBLIC, anon, authenticated;
REVOKE SELECT ON TABLE public.category_overrides_view FROM PUBLIC, anon, authenticated;
REVOKE SELECT ON TABLE public.distinct_cities FROM PUBLIC, anon, authenticated;

-- Keep these legacy views available to trusted server-side maintenance only.
GRANT SELECT ON TABLE public.deduplicated_events TO service_role;
GRANT SELECT ON TABLE public.category_overrides_view TO service_role;
GRANT SELECT ON TABLE public.distinct_cities TO service_role;

-- This helper exposes a supplied user's display name through auth.users. It is
-- used only by category_overrides_view, which is now service-only. Do not leave
-- arbitrary user lookup available to browser roles.
REVOKE EXECUTE ON FUNCTION public.get_curator_name(uuid)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_curator_name(uuid) TO service_role;

-- These two identity helpers are referenced by authenticated-only RLS policies
-- and return data only for auth.uid(). Anonymous execution is unnecessary.
REVOKE EXECUTE ON FUNCTION public.get_my_github_username()
  FROM PUBLIC, anon;
REVOKE EXECUTE ON FUNCTION public.get_my_google_email()
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.get_my_github_username() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_my_google_email() TO authenticated, service_role;

-- pg_net is non-relocatable. Supabase's supported remediation is to drop and
-- recreate it in extensions. Abort if doing so would discard queued requests
-- or stored responses; keep DROP without CASCADE so dependencies also fail
-- closed. The hosted project was checked before authoring this migration.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job) THEN
    RAISE EXCEPTION 'Refusing to move pg_net while scheduled jobs exist';
  END IF;
  IF EXISTS (SELECT 1 FROM net.http_request_queue) THEN
    RAISE EXCEPTION 'Refusing to move pg_net while queued requests exist';
  END IF;
  IF EXISTS (SELECT 1 FROM net._http_response) THEN
    RAISE EXCEPTION 'Refusing to move pg_net while stored responses exist';
  END IF;
END
$$;

CREATE SCHEMA IF NOT EXISTS extensions;
DROP EXTENSION pg_net;
CREATE EXTENSION pg_net WITH SCHEMA extensions;
