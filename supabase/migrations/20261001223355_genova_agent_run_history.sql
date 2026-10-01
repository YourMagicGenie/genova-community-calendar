-- Keep the Genova agent's private run ledger separate from public event data.
-- Browser sessions may read it only when the Auth UUID is in admin_users;
-- trusted Edge Function code is responsible for inserting/updating runs.
CREATE TABLE public.agent_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_mode text NOT NULL
    CHECK (run_mode IN ('discover', 'collect', 'fixture')),
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')),
  requested_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  instruction_revision text NOT NULL
    CHECK (instruction_revision ~ '^[0-9a-f]{40}$'),
  queued_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  candidate_count integer NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
  sources_scanned integer NOT NULL DEFAULT 0 CHECK (sources_scanned >= 0),
  events_found integer NOT NULL DEFAULT 0 CHECK (events_found >= 0),
  events_needing_review integer NOT NULL DEFAULT 0 CHECK (events_needing_review >= 0),
  events_added integer NOT NULL DEFAULT 0 CHECK (events_added >= 0),
  events_updated integer NOT NULL DEFAULT 0 CHECK (events_updated >= 0),
  events_cancelled integer NOT NULL DEFAULT 0 CHECK (events_cancelled >= 0),
  source_failures jsonb NOT NULL DEFAULT '[]'::jsonb
    CHECK (jsonb_typeof(source_failures) = 'array'),
  error_summary text
);

COMMENT ON TABLE public.agent_runs IS
  'Private audit history for manually triggered Genova discovery, collection, and fixture runs.';
COMMENT ON COLUMN public.agent_runs.instruction_revision IS
  'Full Git commit SHA for the versioned AGENT.md instructions used by the run.';
COMMENT ON COLUMN public.agent_runs.source_failures IS
  'Safe source-level failure summaries; never store credentials or full secret-bearing response bodies.';

CREATE INDEX agent_runs_queued_at_idx
  ON public.agent_runs (queued_at DESC);

-- This is deliberately a single in-flight run for the sole-admin pilot.
CREATE UNIQUE INDEX agent_runs_one_inflight_idx
  ON public.agent_runs ((true))
  WHERE status IN ('queued', 'running');

ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.agent_runs FROM anon, authenticated;
GRANT SELECT ON TABLE public.agent_runs TO authenticated;
GRANT ALL ON TABLE public.agent_runs TO service_role;

CREATE POLICY "Admins can view Genova agent runs"
  ON public.agent_runs FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.admin_users
      WHERE user_id = (SELECT auth.uid())
    )
  );
