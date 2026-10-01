-- The cleanup RPC is SECURITY DEFINER and must only be callable by the
-- trusted load-events Edge Function, which uses the service role.
REVOKE EXECUTE ON FUNCTION public.delete_stale_events(text, text[])
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.delete_stale_events(text, text[])
  TO service_role;
