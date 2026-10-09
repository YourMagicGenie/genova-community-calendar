-- Issue #102: retain expired facts, but keep them out of active review and publication.
ALTER TABLE public.genova_event_facts
  ADD COLUMN is_all_day boolean NOT NULL DEFAULT false;

GRANT UPDATE (is_all_day) ON public.genova_event_facts TO authenticated;

CREATE FUNCTION public.genova_occurrence_is_current(
  p_start_time timestamptz,
  p_end_time timestamptz,
  p_is_all_day boolean,
  p_now timestamptz DEFAULT now()
)
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = ''
AS $$
  SELECT CASE
    WHEN p_start_time IS NULL THEN true
    WHEN p_is_all_day THEN
      (COALESCE(p_end_time, p_start_time) AT TIME ZONE 'Europe/Rome')::date >=
      (p_now AT TIME ZONE 'Europe/Rome')::date
    ELSE COALESCE(p_end_time, p_start_time) >= p_now
  END
$$;

REVOKE ALL ON FUNCTION public.genova_occurrence_is_current(timestamptz,timestamptz,boolean,timestamptz)
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.genova_occurrence_is_current(timestamptz,timestamptz,boolean,timestamptz)
  TO authenticated, service_role;

-- The review RPC is security-invoker: the existing admin-only table RLS policy
-- remains the authority for which authenticated users can read these rows.
CREATE FUNCTION public.list_admin_genova_event_review_queue()
RETURNS TABLE (
  id bigint,
  source_uid text,
  title text,
  start_time timestamptz,
  end_time timestamptz,
  is_all_day boolean,
  location text,
  publisher_label text,
  direct_url text,
  category text,
  category_confidence numeric,
  tags text[],
  review_status text,
  evidence_note text,
  last_seen timestamptz,
  superseded_by bigint,
  date_state text
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $$
  SELECT e.id, e.source_uid, e.title, e.start_time, e.end_time, e.is_all_day,
    e.location, e.publisher_label, e.direct_url, e.category,
    e.category_confidence, e.tags, e.review_status, e.evidence_note,
    e.last_seen, e.superseded_by,
    CASE WHEN e.start_time IS NULL THEN 'needs_date_extraction' ELSE 'current' END
  FROM public.genova_event_facts e
  WHERE e.review_status IN ('needs_review', 'validated', 'published')
    AND e.superseded_by IS NULL
    AND public.genova_occurrence_is_current(e.start_time, e.end_time, e.is_all_day)
  ORDER BY e.start_time NULLS FIRST, e.id
  LIMIT 100
$$;

REVOKE ALL ON FUNCTION public.list_admin_genova_event_review_queue() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.list_admin_genova_event_review_queue() TO authenticated, service_role;

DROP FUNCTION public.list_public_genova_events();
CREATE FUNCTION public.list_public_genova_events()
RETURNS TABLE (
  id bigint,
  title text,
  start_time timestamptz,
  end_time timestamptz,
  is_all_day boolean,
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
  SELECT e.id, e.title, e.start_time, e.end_time, e.is_all_day, e.location,
    e.publisher_label AS publisher, e.direct_url AS url, e.category
  FROM public.genova_event_facts e
  JOIN public.feeds f ON f.id = e.feed_id
  WHERE e.review_status = 'published'
    AND e.start_time IS NOT NULL
    AND f.city = 'genova'
    AND f.status = 'active'
    AND public.genova_occurrence_is_current(e.start_time, e.end_time, e.is_all_day)
  ORDER BY e.start_time, e.id
$$;
REVOKE ALL ON FUNCTION public.list_public_genova_events() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.list_public_genova_events() TO anon, authenticated, service_role;

-- Collector imports may retain old database rows, but never add a past
-- occurrence to the active review set. Unknown dates remain visible separately.
CREATE OR REPLACE FUNCTION public.import_genova_luzzati_facts(p_feed_id bigint, p_events jsonb)
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE changed integer;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.feeds WHERE id = p_feed_id AND city = 'genova'
    AND status = 'active' AND feed_type = 'web_index'
    AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/') THEN
    RAISE EXCEPTION 'Luzzati import requires the exact active approved source';
  END IF;
  IF jsonb_typeof(p_events) IS DISTINCT FROM 'array' OR jsonb_array_length(p_events) > 500 THEN
    RAISE EXCEPTION 'invalid event fact array';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_events) event
    WHERE (event ->> 'feed_id')::bigint IS DISTINCT FROM p_feed_id
      OR event ->> 'review_status' IS DISTINCT FROM 'needs_review'
      OR event ->> 'source_uid' NOT LIKE 'genova-luzzati:%'
      OR event ->> 'normalized_url' NOT LIKE 'https://www.spazio-comune.org/prodotto/%'
      OR event ->> 'url' NOT LIKE 'https://www.spazio-comune.org/prodotto/%'
      OR COALESCE(event ->> 'is_all_day', 'false') NOT IN ('true', 'false')) THEN
    RAISE EXCEPTION 'event facts do not match the trusted source/review contract';
  END IF;
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  INSERT INTO public.genova_event_facts (
    feed_id, source_uid, title, start_time, end_time, is_all_day, location, publisher_label,
    direct_url, normalized_url, category, category_confidence, review_status, evidence_note
  )
  SELECT p_feed_id, event ->> 'source_uid', event ->> 'title',
    NULLIF(event ->> 'start_time','')::timestamptz,
    NULLIF(event ->> 'end_time','')::timestamptz,
    COALESCE((event ->> 'is_all_day')::boolean, false),
    NULLIF(event ->> 'location',''), event ->> 'publisher', event ->> 'url',
    event ->> 'normalized_url', NULLIF(event ->> 'category',''),
    NULLIF(event ->> 'category_confidence','')::numeric, 'needs_review', event ->> 'evidence_note'
  FROM jsonb_array_elements(p_events) event
  WHERE public.genova_occurrence_is_current(
      NULLIF(event ->> 'start_time','')::timestamptz,
      NULLIF(event ->> 'end_time','')::timestamptz,
      COALESCE((event ->> 'is_all_day')::boolean, false)
    )
    AND (NULLIF(event ->> 'start_time','') IS NOT NULL OR NOT EXISTS (
      SELECT 1 FROM public.genova_event_facts known
      WHERE known.feed_id = p_feed_id AND known.normalized_url = event ->> 'normalized_url'
        AND known.start_time IS NOT NULL
    ))
  ON CONFLICT (source_uid) DO UPDATE SET
    title = EXCLUDED.title,
    start_time = COALESCE(EXCLUDED.start_time, public.genova_event_facts.start_time),
    end_time = COALESCE(EXCLUDED.end_time, public.genova_event_facts.end_time),
    is_all_day = EXCLUDED.is_all_day,
    location = COALESCE(EXCLUDED.location, public.genova_event_facts.location),
    publisher_label = EXCLUDED.publisher_label, direct_url = EXCLUDED.direct_url,
    category = COALESCE(EXCLUDED.category, public.genova_event_facts.category),
    category_confidence = COALESCE(EXCLUDED.category_confidence, public.genova_event_facts.category_confidence),
    last_seen = now(), evidence_note = EXCLUDED.evidence_note
  WHERE public.genova_event_facts.feed_id = EXCLUDED.feed_id
    AND public.genova_event_facts.normalized_url = EXCLUDED.normalized_url
    AND public.genova_event_facts.review_status = 'needs_review'
    AND public.genova_event_facts.superseded_by IS NULL;
  GET DIAGNOSTICS changed = ROW_COUNT;
  PERFORM public.reconcile_genova_event_placeholders(p_feed_id, ARRAY(
    SELECT event ->> 'normalized_url' FROM jsonb_array_elements(p_events) event
    GROUP BY event ->> 'normalized_url'
    HAVING count(*) = 1 AND count(NULLIF(event ->> 'start_time','')) = 1
  ));
  RETURN changed;
END;
$$;
REVOKE ALL ON FUNCTION public.import_genova_luzzati_facts(bigint,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.import_genova_luzzati_facts(bigint,jsonb) TO service_role;

-- Preserve the all-day precision when an admin correction is audited.
CREATE OR REPLACE FUNCTION public.audit_genova_event_fact_change()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF auth.uid() IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'admin access required' USING ERRCODE = '42501';
  END IF;
  INSERT INTO public.genova_event_fact_audit (
    event_fact_id, source_uid, changed_by, old_values, new_values
  ) VALUES (
    NEW.id, NEW.source_uid, auth.uid(),
    jsonb_build_object(
      'title', OLD.title, 'start_time', OLD.start_time, 'end_time', OLD.end_time,
      'is_all_day', OLD.is_all_day, 'location', OLD.location, 'direct_url', OLD.direct_url,
      'normalized_url', OLD.normalized_url, 'category', OLD.category,
      'category_confidence', OLD.category_confidence, 'tags', OLD.tags,
      'review_status', OLD.review_status, 'evidence_note', OLD.evidence_note
    ),
    jsonb_build_object(
      'title', NEW.title, 'start_time', NEW.start_time, 'end_time', NEW.end_time,
      'is_all_day', NEW.is_all_day, 'location', NEW.location, 'direct_url', NEW.direct_url,
      'normalized_url', NEW.normalized_url, 'category', NEW.category,
      'category_confidence', NEW.category_confidence, 'tags', NEW.tags,
      'review_status', NEW.review_status, 'evidence_note', NEW.evidence_note
    )
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS genova_event_fact_audit_update ON public.genova_event_facts;
CREATE TRIGGER genova_event_fact_audit_update
AFTER UPDATE ON public.genova_event_facts
FOR EACH ROW WHEN (
  OLD.title IS DISTINCT FROM NEW.title OR OLD.start_time IS DISTINCT FROM NEW.start_time
  OR OLD.end_time IS DISTINCT FROM NEW.end_time OR OLD.is_all_day IS DISTINCT FROM NEW.is_all_day
  OR OLD.location IS DISTINCT FROM NEW.location OR OLD.direct_url IS DISTINCT FROM NEW.direct_url
  OR OLD.normalized_url IS DISTINCT FROM NEW.normalized_url OR OLD.category IS DISTINCT FROM NEW.category
  OR OLD.category_confidence IS DISTINCT FROM NEW.category_confidence OR OLD.tags IS DISTINCT FROM NEW.tags
  OR OLD.review_status IS DISTINCT FROM NEW.review_status OR OLD.evidence_note IS DISTINCT FROM NEW.evidence_note
) EXECUTE FUNCTION public.audit_genova_event_fact_change();
