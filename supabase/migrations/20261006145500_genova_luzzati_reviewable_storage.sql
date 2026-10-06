-- First real Genova source: owner-approved registry row, reviewable facts,
-- scan provenance, and a deliberately field-limited public publication table.

ALTER TABLE public.feeds
  DROP CONSTRAINT IF EXISTS feeds_feed_type_check;
ALTER TABLE public.feeds
  ADD CONSTRAINT feeds_feed_type_check
  CHECK (feed_type IN ('ics_url', 'scraper', 'curator', 'web_index'));

ALTER TABLE public.feeds
  ADD COLUMN IF NOT EXISTS request_cadence_minutes integer,
  ADD COLUMN IF NOT EXISTS daily_request_cap integer,
  ADD COLUMN IF NOT EXISTS last_attempt_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_success_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_result text;

ALTER TABLE public.feeds
  DROP CONSTRAINT IF EXISTS feeds_request_cadence_minutes_check,
  ADD CONSTRAINT feeds_request_cadence_minutes_check
    CHECK (request_cadence_minutes IS NULL OR request_cadence_minutes >= 60),
  DROP CONSTRAINT IF EXISTS feeds_daily_request_cap_check,
  ADD CONSTRAINT feeds_daily_request_cap_check
    CHECK (daily_request_cap IS NULL OR daily_request_cap BETWEEN 1 AND 24),
  DROP CONSTRAINT IF EXISTS feeds_last_result_check,
  ADD CONSTRAINT feeds_last_result_check
    CHECK (last_result IS NULL OR last_result IN ('succeeded', 'blocked', 'skipped', 'failed'));

INSERT INTO public.feeds (
  city, url, name, status, feed_type, publisher_url, discovery_method,
  request_cadence_minutes, daily_request_cap
)
VALUES (
  'genova',
  'https://www.spazio-comune.org/categoria-prodotto/eventi/',
  'Giardini Luzzati / Spazio Comune',
  'active',
  'web_index',
  'https://www.spazio-comune.org/',
  'manual',
  1440,
  1
)
ON CONFLICT (city, url) DO UPDATE SET
  name = EXCLUDED.name,
  status = 'active',
  feed_type = EXCLUDED.feed_type,
  publisher_url = EXCLUDED.publisher_url,
  discovery_method = EXCLUDED.discovery_method,
  request_cadence_minutes = EXCLUDED.request_cadence_minutes,
  daily_request_cap = EXCLUDED.daily_request_cap;

INSERT INTO public.feed_source_reviews (
  city, feed_url, source_provenance, access_notes, genova_fit,
  discovery_reason, reviewed_at
)
VALUES (
  'genova',
  'https://www.spazio-comune.org/categoria-prodotto/eventi/',
  'Owner-selected Giardini Luzzati / Spazio Comune public event index; verified by Issue #50.',
  'Issue #50: robots.txt HTTP 200 allowed the exact event-index path; index HTTP 200. One index request per day in the pilot; no event-detail crawling.',
  'confirmed',
  'First owner-whitelisted real Genova source for Issue #51.',
  now()
)
ON CONFLICT (city, feed_url) DO UPDATE SET
  source_provenance = EXCLUDED.source_provenance,
  access_notes = EXCLUDED.access_notes,
  genova_fit = EXCLUDED.genova_fit,
  discovery_reason = EXCLUDED.discovery_reason,
  reviewed_at = EXCLUDED.reviewed_at;

CREATE TABLE public.genova_event_candidates (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  feed_id bigint NOT NULL REFERENCES public.feeds(id) ON DELETE CASCADE,
  title text NOT NULL CHECK (btrim(title) <> ''),
  start_time timestamptz,
  end_time timestamptz,
  location text,
  publisher text NOT NULL CHECK (btrim(publisher) <> ''),
  event_url text NOT NULL CHECK (event_url ~ '^https://'),
  normalized_url text NOT NULL CHECK (normalized_url ~ '^https://'),
  source_uid text NOT NULL UNIQUE,
  category text,
  category_confidence numeric(4,3)
    CHECK (category_confidence IS NULL OR category_confidence BETWEEN 0 AND 1),
  review_status text NOT NULL DEFAULT 'needs_review'
    CHECK (review_status IN ('needs_review', 'approved', 'published', 'rejected')),
  first_seen timestamptz NOT NULL DEFAULT now(),
  last_seen timestamptz NOT NULL DEFAULT now(),
  CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time)
);

CREATE UNIQUE INDEX genova_event_candidates_occurrence_idx
  ON public.genova_event_candidates (
    feed_id,
    normalized_url,
    coalesce(start_time, '-infinity'::timestamptz)
  );

CREATE INDEX genova_event_candidates_review_idx
  ON public.genova_event_candidates (review_status, last_seen DESC);

ALTER TABLE public.genova_event_candidates ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_event_candidates FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.genova_event_candidates TO authenticated;
GRANT ALL ON TABLE public.genova_event_candidates TO service_role;

CREATE POLICY "Admins can review Genova event candidates"
  ON public.genova_event_candidates FOR ALL TO authenticated
  USING ((SELECT auth.uid()) IN (SELECT user_id FROM public.admin_users))
  WITH CHECK ((SELECT auth.uid()) IN (SELECT user_id FROM public.admin_users));

CREATE TABLE public.genova_source_scans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid,
  feed_id bigint NOT NULL REFERENCES public.feeds(id) ON DELETE CASCADE,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  collector_revision text NOT NULL CHECK (collector_revision ~ '^[0-9a-f]{40}$'),
  requested_index_url text NOT NULL CHECK (requested_index_url ~ '^https://'),
  robots_decision text NOT NULL
    CHECK (robots_decision IN ('allowed', 'missing_no_rules', 'disallowed', 'unavailable')),
  robots_http_status integer CHECK (robots_http_status IS NULL OR robots_http_status BETWEEN 100 AND 599),
  page_http_status integer CHECK (page_http_status IS NULL OR page_http_status BETWEEN 100 AND 599),
  request_count integer NOT NULL DEFAULT 0 CHECK (request_count BETWEEN 0 AND 2),
  outcome text NOT NULL CHECK (outcome IN ('succeeded', 'blocked', 'skipped', 'failed')),
  facts_extracted integer NOT NULL DEFAULT 0 CHECK (facts_extracted >= 0),
  error_summary text CHECK (error_summary IS NULL OR length(error_summary) <= 500)
);

CREATE INDEX genova_source_scans_feed_started_idx
  ON public.genova_source_scans (feed_id, started_at DESC);

ALTER TABLE public.genova_source_scans ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_source_scans FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.genova_source_scans TO authenticated;
GRANT ALL ON TABLE public.genova_source_scans TO service_role;

CREATE POLICY "Admins can view Genova source scans"
  ON public.genova_source_scans FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) IN (SELECT user_id FROM public.admin_users));

CREATE TABLE public.genova_public_events (
  candidate_id bigint PRIMARY KEY REFERENCES public.genova_event_candidates(id) ON DELETE CASCADE,
  title text NOT NULL,
  start_time timestamptz NOT NULL,
  end_time timestamptz,
  location text,
  publisher text NOT NULL,
  event_url text NOT NULL,
  category text,
  published_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.genova_public_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_public_events FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.genova_public_events TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON TABLE public.genova_public_events TO authenticated;
GRANT ALL ON TABLE public.genova_public_events TO service_role;

CREATE POLICY "Public can read published Genova event fields"
  ON public.genova_public_events FOR SELECT TO anon, authenticated
  USING (true);

CREATE POLICY "Admins can publish Genova event candidates"
  ON public.genova_public_events FOR ALL TO authenticated
  USING ((SELECT auth.uid()) IN (SELECT user_id FROM public.admin_users))
  WITH CHECK (
    (SELECT auth.uid()) IN (SELECT user_id FROM public.admin_users)
    AND EXISTS (
      SELECT 1
      FROM public.genova_event_candidates candidate
      WHERE candidate.id = candidate_id
        AND candidate.review_status IN ('approved', 'published')
        AND candidate.start_time IS NOT NULL
        AND candidate.title = genova_public_events.title
        AND candidate.start_time = genova_public_events.start_time
        AND candidate.end_time IS NOT DISTINCT FROM genova_public_events.end_time
        AND candidate.location IS NOT DISTINCT FROM genova_public_events.location
        AND candidate.publisher = genova_public_events.publisher
        AND candidate.event_url = genova_public_events.event_url
        AND candidate.category IS NOT DISTINCT FROM genova_public_events.category
    )
  );
