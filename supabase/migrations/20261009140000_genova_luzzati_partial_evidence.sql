-- Keep the Luzzati collector's concise date/time clues with its private facts.
-- Bulletin rows use the same core evidence keys plus PDF page/bounding-box data.
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
      OR COALESCE(event ->> 'is_all_day', 'false') NOT IN ('true', 'false')
      OR jsonb_typeof(event -> 'source_metadata') IS DISTINCT FROM 'object'
      OR octet_length(COALESCE(event -> 'source_metadata', '{}'::jsonb)::text) > 16384
      OR (event -> 'source_metadata') - ARRAY[
        'kind', 'source_url', 'field_evidence', 'unresolved_reasons', 'date_precision', 'partial_dates'
      ]::text[] <> '{}'::jsonb
      OR event #>> '{source_metadata,kind}' IS DISTINCT FROM 'source_page'
      OR event #>> '{source_metadata,source_url}' IS DISTINCT FROM event ->> 'normalized_url'
      OR COALESCE(jsonb_typeof(event #> '{source_metadata,field_evidence}'), 'null') <> 'object'
      OR octet_length(COALESCE(event #> '{source_metadata,field_evidence}', '{}'::jsonb)::text) > 8192
      OR (event #> '{source_metadata,field_evidence}') - ARRAY['date', 'time']::text[] <> '{}'::jsonb
      OR EXISTS (
        SELECT 1 FROM jsonb_each(COALESCE(event #> '{source_metadata,field_evidence}', '{}'::jsonb)) evidence
        WHERE jsonb_typeof(evidence.value) <> 'object'
          OR evidence.value - ARRAY['text', 'method']::text[] <> '{}'::jsonb
          OR jsonb_typeof(evidence.value -> 'text') IS DISTINCT FROM 'string'
          OR length(evidence.value ->> 'text') NOT BETWEEN 1 AND 240
          OR evidence.value ->> 'method' IS DISTINCT FROM 'visible_event_text'
      )
      OR COALESCE(jsonb_typeof(event #> '{source_metadata,unresolved_reasons}'), 'null') <> 'array'
      OR jsonb_array_length(COALESCE(event #> '{source_metadata,unresolved_reasons}', '[]'::jsonb)) > 12
      OR EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(event #> '{source_metadata,unresolved_reasons}', '[]'::jsonb)) reason
        WHERE jsonb_typeof(reason) <> 'string' OR length(reason #>> '{}') NOT BETWEEN 1 AND 160)
      OR COALESCE(event #>> '{source_metadata,date_precision}', '') NOT IN
        ('day', 'range', 'end_only', 'weekday_only', 'unknown', 'yearless', 'unresolved', 'listed_dates')
      OR COALESCE(jsonb_typeof(event #> '{source_metadata,partial_dates}'), 'null') <> 'array'
      OR jsonb_array_length(COALESCE(event #> '{source_metadata,partial_dates}', '[]'::jsonb)) > 31
      OR EXISTS (
        SELECT 1 FROM jsonb_array_elements(COALESCE(event #> '{source_metadata,partial_dates}', '[]'::jsonb)) partial
        WHERE jsonb_typeof(partial) <> 'object'
          OR partial - ARRAY['day', 'month']::text[] <> '{}'::jsonb
          OR jsonb_typeof(partial -> 'day') IS DISTINCT FROM 'number'
          OR jsonb_typeof(partial -> 'month') IS DISTINCT FROM 'number'
          OR CASE WHEN jsonb_typeof(partial -> 'day') = 'number'
                    AND jsonb_typeof(partial -> 'month') = 'number'
                  THEN (partial ->> 'day')::numeric <> trunc((partial ->> 'day')::numeric)
                    OR (partial ->> 'month')::numeric <> trunc((partial ->> 'month')::numeric)
                  ELSE true END
          OR CASE WHEN jsonb_typeof(partial -> 'day') = 'number'
                    AND jsonb_typeof(partial -> 'month') = 'number'
                  THEN (partial ->> 'day')::numeric NOT BETWEEN 1 AND
                    CASE (partial ->> 'month')::integer
                      WHEN 1 THEN 31 WHEN 2 THEN 29 WHEN 3 THEN 31 WHEN 4 THEN 30
                      WHEN 5 THEN 31 WHEN 6 THEN 30 WHEN 7 THEN 31 WHEN 8 THEN 31
                      WHEN 9 THEN 30 WHEN 10 THEN 31 WHEN 11 THEN 30 WHEN 12 THEN 31
                      ELSE 0 END
                  ELSE true END
          OR CASE WHEN jsonb_typeof(partial -> 'month') = 'number'
                  THEN (partial ->> 'month')::numeric NOT BETWEEN 1 AND 12 ELSE true END
      )
      OR (event #>> '{source_metadata,date_precision}' IN ('yearless', 'unresolved', 'listed_dates')
          AND NULLIF(event ->> 'start_time', '') IS NOT NULL)
  ) THEN
    RAISE EXCEPTION 'event facts do not match the bounded private evidence contract';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_events) event
    WHERE event ? 'category_suggestions'
      AND jsonb_typeof(event -> 'category_suggestions') IS DISTINCT FROM 'array') THEN
    RAISE EXCEPTION 'category suggestions must be a JSON array';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(p_events) event
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(event -> 'category_suggestions', '[]'::jsonb)) suggestion
    WHERE suggestion ->> 'category' NOT IN (
      'music', 'theatre-performance', 'art-exhibitions', 'sports', 'food-drink',
      'festivals-markets', 'talks-workshops', 'family', 'outdoors-tours', 'community-social'
    ) OR jsonb_typeof(suggestion -> 'confidence') IS DISTINCT FROM 'number'
      OR (suggestion ->> 'confidence')::numeric NOT BETWEEN 0 AND 1
      OR jsonb_typeof(suggestion -> 'evidence') IS DISTINCT FROM 'string'
      OR length(suggestion ->> 'evidence') > 160
  ) THEN
    RAISE EXCEPTION 'invalid category suggestion';
  END IF;
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  INSERT INTO public.genova_event_facts (
    feed_id, source_uid, title, start_time, end_time, is_all_day, location,
    publisher_label, direct_url, normalized_url, category, category_confidence,
    category_suggestions, review_status, evidence_note, source_metadata
  )
  SELECT p_feed_id, event ->> 'source_uid', event ->> 'title',
    NULLIF(event ->> 'start_time','')::timestamptz,
    NULLIF(event ->> 'end_time','')::timestamptz,
    COALESCE((event ->> 'is_all_day')::boolean, false), NULLIF(event ->> 'location',''),
    event ->> 'publisher', event ->> 'url', event ->> 'normalized_url',
    NULLIF(event ->> 'category',''), NULLIF(event ->> 'category_confidence','')::numeric,
    COALESCE(event -> 'category_suggestions', '[]'::jsonb),
    'needs_review', event ->> 'evidence_note', event -> 'source_metadata'
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
    category_suggestions = EXCLUDED.category_suggestions,
    source_metadata = EXCLUDED.source_metadata,
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
