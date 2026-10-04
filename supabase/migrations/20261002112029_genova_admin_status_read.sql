-- Let authenticated sessions check only their own admin marker.
-- The existing row-level policy limits visibility to auth.uid() = user_id.
REVOKE ALL ON TABLE public.admin_users FROM anon, authenticated;
GRANT SELECT ON TABLE public.admin_users TO authenticated;
GRANT ALL ON TABLE public.admin_users TO service_role;
