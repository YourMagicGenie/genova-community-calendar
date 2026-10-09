-- Persist reusable category suggestions beside private event facts. Admins can
-- inspect them, but only the trusted importer may replace the suggestion data.
ALTER TABLE public.genova_event_facts
  ADD COLUMN category_suggestions jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD CONSTRAINT genova_event_facts_category_suggestions_array
    CHECK (jsonb_typeof(category_suggestions) = 'array'
      AND jsonb_array_length(category_suggestions) <= 3);

-- Extend the already field-limited admin queue without reverting #102's
-- expiration filtering or bypassing its security-invoker RLS boundary.
DROP FUNCTION public.list_admin_genova_event_review_queue();
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
  category_suggestions jsonb,
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
    e.category_confidence, e.category_suggestions, e.tags, e.review_status,
    e.evidence_note, e.last_seen, e.superseded_by,
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
      OR event ->> 'url' NOT LIKE 'https://www.spazio-comune.org/prodotto/%') THEN
    RAISE EXCEPTION 'event facts do not match the trusted source/review contract';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_events) event
    WHERE event ? 'category_suggestions'
      AND jsonb_typeof(event -> 'category_suggestions') IS DISTINCT FROM 'array') THEN
    RAISE EXCEPTION 'category suggestions must be a JSON array';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM jsonb_array_elements(p_events) event
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(event -> 'category_suggestions', '[]'::jsonb)) suggestion
    WHERE suggestion ->> 'category' NOT IN (
      'music', 'theatre-performance', 'art-exhibitions', 'sports', 'food-drink',
      'festivals-markets', 'talks-workshops', 'family', 'outdoors-tours', 'community-social'
    )
      OR jsonb_typeof(suggestion -> 'confidence') IS DISTINCT FROM 'number'
      OR (suggestion ->> 'confidence')::numeric NOT BETWEEN 0 AND 1
      OR jsonb_typeof(suggestion -> 'evidence') IS DISTINCT FROM 'string'
      OR length(suggestion ->> 'evidence') > 160
  ) THEN
    RAISE EXCEPTION 'invalid category suggestion';
  END IF;
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  INSERT INTO public.genova_event_facts (
    feed_id, source_uid, title, start_time, end_time, location, publisher_label,
    direct_url, normalized_url, category, category_confidence, category_suggestions,
    review_status, evidence_note
  )
  SELECT p_feed_id, event ->> 'source_uid', event ->> 'title',
    NULLIF(event ->> 'start_time','')::timestamptz,
    NULLIF(event ->> 'end_time','')::timestamptz, NULLIF(event ->> 'location',''),
    event ->> 'publisher', event ->> 'url', event ->> 'normalized_url',
    NULLIF(event ->> 'category',''), NULLIF(event ->> 'category_confidence','')::numeric,
    COALESCE(event -> 'category_suggestions', '[]'::jsonb),
    'needs_review', event ->> 'evidence_note'
  FROM jsonb_array_elements(p_events) event
  WHERE NULLIF(event ->> 'start_time','') IS NOT NULL OR NOT EXISTS (
    SELECT 1 FROM public.genova_event_facts known
    WHERE known.feed_id = p_feed_id AND known.normalized_url = event ->> 'normalized_url'
      AND known.start_time IS NOT NULL
  )
  ON CONFLICT (source_uid) DO UPDATE SET
    title = EXCLUDED.title,
    start_time = COALESCE(EXCLUDED.start_time, public.genova_event_facts.start_time),
    end_time = COALESCE(EXCLUDED.end_time, public.genova_event_facts.end_time),
    location = COALESCE(EXCLUDED.location, public.genova_event_facts.location),
    publisher_label = EXCLUDED.publisher_label, direct_url = EXCLUDED.direct_url,
    category = COALESCE(EXCLUDED.category, public.genova_event_facts.category),
    category_confidence = COALESCE(EXCLUDED.category_confidence, public.genova_event_facts.category_confidence),
    category_suggestions = EXCLUDED.category_suggestions,
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
