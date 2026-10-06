-- Issue #51: first whitelisted Genova source persistence and review boundary.
-- Reuse public.feeds as the source registry; keep event facts and scan provenance
-- separate, private until reviewed, and field-limit the public read path.

ALTER TABLE public.feeds
  DROP CONSTRAINT IF EXISTS feeds_feed_type_check;

ALTER TABLE public.feeds
  ADD CONSTRAINT feeds_feed_type_check
  CHECK (feed_type IN ('ics_url', 'scraper', 'curator', 'web_index'));

INSERT INTO public.feeds (
  city, url, name, status, feed_type, publisher_url, discovery_method
) VALUES (
  'genova',
  'https://www.spazio-comune.org/categoria-prodotto/eventi/',
  'Giardini Luzzati / Spazio Comune',
  'active',
  'web_index',
  'https://www.spazio-comune.org/',
  'manual'
)
ON CONFLICT (city, url) DO UPDATE
SET name = EXCLUDED.name,
    status = 'active',
    feed_type = EXCLUDED.feed_type,
    publisher_url = EXCLUDED.publisher_url,
    discovery_method = EXCLUDED.discovery_method;

INSERT INTO public.feed_source_reviews (
  city, feed_url, source_provenance, access_notes, genova_fit, discovery_reason, reviewed_at
) VALUES (
  'genova',
  'https://www.spazio-comune.org/categoria-prodotto/eventi/',
  'Owner-selected first source; Issue #50 verified the exact public event index.',
  'Robots-aware, one public index request per manual pilot run; no event detail fan-out.',
  'confirmed',
  'First bounded real-source pilot for Issue #51.',
  now()
)
ON CONFLICT (city, feed_url) DO UPDATE
SET source_provenance = EXCLUDED.source_provenance,
    access_notes = EXCLUDED.access_notes,
    genova_fit = EXCLUDED.genova_fit,
    discovery_reason = EXCLUDED.discovery_reason,
    reviewed_at = EXCLUDED.reviewed_at;

CREATE TABLE public.genova_event_facts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  feed_id bigint NOT NULL REFERENCES public.feeds(id) ON DELETE RESTRICT,
  source_uid text NOT NULL UNIQUE,
  title text NOT NULL CHECK (btrim(title) <> ''),
  start_time timestamptz,
  end_time timestamptz,
  location text,
  publisher_label text NOT NULL CHECK (btrim(publisher_label) <> ''),
  direct_url text NOT NULL CHECK (direct_url ~ '^https://'),
  normalized_url text NOT NULL CHECK (normalized_url ~ '^https://'),
  category text,
  category_confidence numeric(4,3)
    CHECK (category_confidence IS NULL OR (category_confidence >= 0 AND category_confidence <= 1)),
  review_status text NOT NULL DEFAULT 'needs_review'
    CHECK (review_status IN ('needs_review', 'validated', 'published', 'rejected')),
  evidence_note text,
  first_seen timestamptz NOT NULL DEFAULT now(),
  last_seen timestamptz NOT NULL DEFAULT now(),
  CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time)
);

CREATE UNIQUE INDEX genova_event_facts_occurrence_unique
  ON public.genova_event_facts (
    feed_id,
    normalized_url,
    COALESCE(start_time, '-infinity'::timestamptz)
  );

CREATE INDEX genova_event_facts_review_idx
  ON public.genova_event_facts (review_status, start_time);

ALTER TABLE public.genova_event_facts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_event_facts FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE ON TABLE public.genova_event_facts TO authenticated;
GRANT ALL ON TABLE public.genova_event_facts TO service_role;
REVOKE ALL ON SEQUENCE public.genova_event_facts_id_seq FROM PUBLIC, anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.genova_event_facts_id_seq TO service_role;

CREATE POLICY "Admins can review Genova event facts"
  ON public.genova_event_facts
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_users
      WHERE user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Admins can update Genova event facts"
  ON public.genova_event_facts
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_users
      WHERE user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.admin_users
      WHERE user_id = (SELECT auth.uid())
    )
  );

CREATE FUNCTION public.guard_genova_event_publication()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF NEW.review_status = 'published' THEN
    IF NEW.start_time IS NULL THEN
      RAISE EXCEPTION 'published Genova events require a start time';
    END IF;
    IF NOT EXISTS (
      SELECT 1
      FROM public.feeds f
      WHERE f.id = NEW.feed_id
        AND f.city = 'genova'
        AND f.status = 'active'
    ) THEN
      RAISE EXCEPTION 'published Genova events require an active approved source';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER genova_event_publication_guard
BEFORE INSERT OR UPDATE OF review_status, start_time, feed_id
ON public.genova_event_facts
FOR EACH ROW EXECUTE FUNCTION public.guard_genova_event_publication();

REVOKE ALL ON FUNCTION public.guard_genova_event_publication() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.guard_genova_event_publication() TO service_role;

CREATE TABLE public.genova_source_scans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id uuid REFERENCES public.agent_runs(id) ON DELETE SET NULL,
  feed_id bigint NOT NULL REFERENCES public.feeds(id) ON DELETE RESTRICT,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  collector_revision text NOT NULL CHECK (collector_revision ~ '^[0-9a-f]{40}$'),
  requested_url text NOT NULL CHECK (requested_url ~ '^https://'),
  robots_decision text NOT NULL
    CHECK (robots_decision IN ('allowed', 'disallowed', 'missing_no_rules', 'unavailable', 'not_checked')),
  robots_http_status integer,
  page_http_status integer,
  request_count integer NOT NULL DEFAULT 0 CHECK (request_count >= 0 AND request_count <= 2),
  outcome text NOT NULL
    CHECK (outcome IN ('succeeded', 'skipped', 'failed')),
  events_found integer NOT NULL DEFAULT 0 CHECK (events_found >= 0),
  error_summary text,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.genova_source_scans ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_source_scans FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.genova_source_scans TO authenticated;
GRANT ALL ON TABLE public.genova_source_scans TO service_role;

CREATE POLICY "Admins can view Genova source scans"
  ON public.genova_source_scans
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_users
      WHERE user_id = (SELECT auth.uid())
    )
  );

CREATE OR REPLACE FUNCTION public.list_public_genova_events()
RETURNS TABLE (
  id bigint,
  title text,
  start_time timestamptz,
  end_time timestamptz,
  location text,
  publisher text,
  url text,
  category text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    e.id,
    e.title,
    e.start_time,
    e.end_time,
    e.location,
    e.publisher_label AS publisher,
    e.direct_url AS url,
    e.category
  FROM public.genova_event_facts e
  JOIN public.feeds f ON f.id = e.feed_id
  WHERE e.review_status = 'published'
    AND e.start_time IS NOT NULL
    AND f.city = 'genova'
    AND f.status = 'active'
  ORDER BY e.start_time, e.id
$$;

REVOKE ALL ON FUNCTION public.list_public_genova_events() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.list_public_genova_events() TO anon, authenticated, service_role;
