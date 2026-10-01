# Protecting the event writer

`load-events` is a privileged server function: it uses the Supabase service-role
key and can insert, update, and remove events. Its public caller must never be
trusted to supply a city or event list without server-side checks.

## What the function enforces

- Only `POST` requests are accepted; `OPTIONS` is limited to CORS preflight.
- Every `POST` needs the `x-load-events-token` header. The matching
  `LOAD_EVENTS_TOKEN` must be set in the Supabase Edge Function secrets.
- Missing or short server configuration fails closed. A missing or incorrect
  request token is rejected before the function creates a database client.
- Bodies are limited to 10 MiB and 10,000 events. Direct events need a
  `source_uid`, title, and timezone-qualified ISO 8601 `start_time`.
- Direct and legacy modes accept Genova only. The legacy mode reads from this
  repository and never discovers inherited city folders or falls back to the
  upstream repository.
- The `delete_stale_events` database function is not an anonymous API: only
  `service_role` can execute it. Its `SECURITY DEFINER` privileges cannot be
  reached by calling the RPC directly as `anon` or `authenticated`.

These checks do not make an endpoint ready to deploy. No Genova backend or
writer workflow is configured by this repository yet.

## Configure credentials when a Genova backend is chosen

1. Generate a random token with at least 32 characters outside the repository,
   for example with `openssl rand -hex 32`. Do not paste it into chat, an issue,
   a workflow file, or any committed file.
2. Add the token as `LOAD_EVENTS_TOKEN` in the chosen Supabase project's Edge
   Function secrets and as a GitHub Actions repository secret of the same name.
3. This function sets `verify_jwt = false` in `supabase/config.toml`, because
   the trusted collector is not a signed-in user sending an Authorization JWT.
   The function's own token check is mandatory and runs before any database
   access. A future server-side workflow should send the project's publishable
   key in `apikey` and the secret in `x-load-events-token`; the publishable key
   alone does not authorize writes.
4. Do not pass the token from browser code. Only a trusted server-side job may
   call the writer.

## Rotate the token

The function accepts one token at a time. For rotation, replace the value in
both Supabase and GitHub Actions in one maintenance window, then verify a test
request with the new value succeeds and the old value is rejected. If the two
settings differ during the update, writes will fail closed until they match.

For the platform's API-key and Edge Function authorization headers, see the
[Supabase authorization-header guide](https://supabase.com/docs/guides/functions/auth-headers).
