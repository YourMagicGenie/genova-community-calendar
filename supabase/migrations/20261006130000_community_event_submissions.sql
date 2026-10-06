-- Visitor proposals are private until a registered admin approves an event.
-- This table is independent of the approved-source directory.
CREATE TABLE public.event_submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL CHECK (length(btrim(title)) BETWEEN 3 AND 160),
  start_time timestamptz NOT NULL,
  end_time timestamptz CHECK (end_time IS NULL OR end_time > start_time),
  description text NOT NULL CHECK (length(btrim(description)) BETWEEN 10 AND 4000),
  location text CHECK (location IS NULL OR length(location) <= 200),
  url text CHECK (url IS NULL OR (length(url) <= 500 AND url ~* '^https://[^[:space:]]+$')),
  submitter_name text CHECK (submitter_name IS NULL OR length(submitter_name) <= 100),
  contact_email text CHECK (contact_email IS NULL OR (length(contact_email) <= 254 AND contact_email ~* '^[^@[:space:]]+@[^@[:space:]]+$')),
  rights_confirmed boolean NOT NULL DEFAULT false CHECK (rights_confirmed),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'withdrawn')),
  created_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  review_note text,
  published_event_id bigint UNIQUE REFERENCES public.events(id) ON DELETE SET NULL,
  CONSTRAINT event_submission_review_state CHECK (
    (status = 'pending' AND reviewed_at IS NULL AND reviewed_by IS NULL AND published_event_id IS NULL)
    OR (status <> 'pending' AND reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)
  )
);

-- Applying the migration must not open a public intake endpoint. Activate
-- this server-owned switch only after the live route and privacy notice exist.
CREATE TABLE public.community_submission_settings (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  accepting boolean NOT NULL DEFAULT false
);
INSERT INTO public.community_submission_settings(singleton, accepting) VALUES (true, false);
ALTER TABLE public.community_submission_settings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.community_submission_settings FROM PUBLIC, anon, authenticated;
GRANT SELECT, UPDATE ON public.community_submission_settings TO service_role;

CREATE INDEX event_submissions_review_idx ON public.event_submissions (status, created_at DESC);
ALTER TABLE public.event_submissions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.event_submissions FROM PUBLIC, anon, authenticated;
-- Browser clients may supply only proposal fields; they cannot set an ID,
-- review status, timestamp, reviewer, or published event reference.
GRANT INSERT (title, start_time, end_time, description, location, url,
              submitter_name, contact_email, rights_confirmed)
  ON public.event_submissions TO anon, authenticated;
GRANT SELECT ON public.event_submissions TO authenticated;
GRANT UPDATE (title, start_time, end_time, description, location, url,
              submitter_name, contact_email)
  ON public.event_submissions TO authenticated;
GRANT ALL ON public.event_submissions TO service_role;

CREATE POLICY "Visitors propose pending events" ON public.event_submissions
  FOR INSERT TO anon, authenticated
  WITH CHECK (status = 'pending' AND reviewed_at IS NULL AND reviewed_by IS NULL
    AND published_event_id IS NULL AND rights_confirmed);
CREATE POLICY "Admin reads event proposals" ON public.event_submissions
  FOR SELECT TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM public.admin_users));
CREATE POLICY "Admin edits event proposals" ON public.event_submissions
  FOR UPDATE TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM public.admin_users))
  WITH CHECK (auth.uid() IN (SELECT user_id FROM public.admin_users));

-- A bounded public intake even if the endpoint is called directly instead of
-- through the form. Serialize the count so simultaneous inserts cannot evade it.
-- A future higher-volume intake can add a challenge and per-client limits.
CREATE FUNCTION public.limit_event_submissions() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.community_submission_settings
                 WHERE singleton AND accepting) THEN
    RAISE EXCEPTION 'community event intake is not enabled'
      USING ERRCODE = '42501';
  END IF;
  PERFORM pg_advisory_xact_lock(20261006, 68);
  IF (SELECT count(*) FROM public.event_submissions
      WHERE created_at > now() - interval '1 day') >= 50 THEN
    RAISE EXCEPTION 'event submission intake is full; try again tomorrow'
      USING ERRCODE = 'P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM public.event_submissions
             WHERE created_at > now() - interval '1 day'
               AND lower(btrim(title)) = lower(btrim(NEW.title))
               AND start_time = NEW.start_time) THEN
    RAISE EXCEPTION 'this event was already proposed recently'
      USING ERRCODE = '23505';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.limit_event_submissions() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER limit_event_submissions_before_insert
  BEFORE INSERT ON public.event_submissions FOR EACH ROW
  EXECUTE FUNCTION public.limit_event_submissions();

-- The only transition into or out of publication is this guarded function.
-- Event facts can be corrected later by the admin; the sync trigger below
-- updates an already approved row without changing its stable source_uid.
CREATE FUNCTION public.review_event_submission(p_id uuid, p_action text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE proposal public.event_submissions%ROWTYPE;
DECLARE event_id bigint;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'admin access required' USING ERRCODE = '42501';
  END IF;
  IF p_action NOT IN ('approve', 'reject', 'withdraw') THEN
    RAISE EXCEPTION 'unknown review action' USING ERRCODE = '22023';
  END IF;
  SELECT * INTO proposal FROM public.event_submissions WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'submission not found' USING ERRCODE = 'P0002'; END IF;
  IF p_action IN ('approve', 'reject') AND proposal.status <> 'pending' THEN
    RAISE EXCEPTION 'submission already reviewed' USING ERRCODE = '22023';
  END IF;
  IF p_action = 'withdraw' AND proposal.status <> 'approved' THEN
    RAISE EXCEPTION 'only approved submissions can be withdrawn' USING ERRCODE = '22023';
  END IF;

  IF p_action = 'approve' THEN
    INSERT INTO public.events (title, start_time, end_time, description,
                               location, url, city, source, source_id, source_uid)
    VALUES (proposal.title, proposal.start_time, proposal.end_time,
            proposal.description, proposal.location, proposal.url, 'genova',
            'Porto Aperto community', 'community_submission', 'community:' || proposal.id::text)
    RETURNING id INTO event_id;
    UPDATE public.event_submissions
      SET status = 'approved', reviewed_by = auth.uid(), reviewed_at = now(),
          published_event_id = event_id WHERE id = p_id;
  ELSIF p_action = 'reject' THEN
    UPDATE public.event_submissions
      SET status = 'rejected', reviewed_by = auth.uid(), reviewed_at = now()
      WHERE id = p_id;
  ELSE
    DELETE FROM public.events WHERE id = proposal.published_event_id
      AND source_uid = 'community:' || proposal.id::text;
    UPDATE public.event_submissions SET status = 'withdrawn', published_event_id = NULL,
      reviewed_by = auth.uid(), reviewed_at = now() WHERE id = p_id;
  END IF;
  RETURN p_action;
END;
$$;
REVOKE ALL ON FUNCTION public.review_event_submission(uuid, text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.review_event_submission(uuid, text) TO authenticated;

CREATE FUNCTION public.sync_approved_submission() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF NEW.status = 'approved' AND NEW.published_event_id IS NOT NULL THEN
    UPDATE public.events SET title = NEW.title, start_time = NEW.start_time,
      end_time = NEW.end_time, description = NEW.description, location = NEW.location,
      url = NEW.url WHERE id = NEW.published_event_id
      AND source_uid = 'community:' || NEW.id::text;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.sync_approved_submission() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER sync_approved_submission_after_edit
  AFTER UPDATE OF title, start_time, end_time, description, location, url
  ON public.event_submissions FOR EACH ROW
  EXECUTE FUNCTION public.sync_approved_submission();

-- Extend the source-publication route with explicitly approved community
-- proposals. These are individual submissions, not approved crawler sources.
-- Keep its eight-column contract so the forthcoming public calendar can use
-- one listing route for both kinds of events.
CREATE OR REPLACE FUNCTION public.list_public_genova_events()
RETURNS TABLE (
  id bigint, title text, start_time timestamptz, end_time timestamptz,
  location text, publisher text, url text, category text
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $function$
  SELECT e.id, e.title, e.start_time, e.end_time, e.location,
         e.publisher_label, e.direct_url, e.category
  FROM public.genova_event_facts e
  JOIN public.feeds f ON f.id = e.feed_id
  WHERE e.review_status = 'published'
    AND e.start_time IS NOT NULL
    AND f.city = 'genova'
    AND f.status = 'active'
  UNION ALL
  SELECT s.published_event_id, s.title, s.start_time, s.end_time, s.location,
         'Porto Aperto community'::text, s.url, NULL::text
  FROM public.event_submissions s
  JOIN public.events e ON e.id = s.published_event_id
    AND e.source_uid = 'community:' || s.id::text
  WHERE s.status = 'approved'
  ORDER BY start_time, id
$function$;

-- Descriptions are provided by the submitter and reviewed individually.
-- Keep private contact and review notes out of this detail endpoint.
CREATE FUNCTION public.get_public_community_description(p_event_id bigint)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $function$
  SELECT s.description
  FROM public.event_submissions s
  JOIN public.events e ON e.id = s.published_event_id
    AND e.source_uid = 'community:' || s.id::text
  WHERE s.status = 'approved' AND s.published_event_id = p_event_id
$function$;
REVOKE ALL ON FUNCTION public.get_public_community_description(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_public_community_description(bigint)
  TO anon, authenticated, service_role;
