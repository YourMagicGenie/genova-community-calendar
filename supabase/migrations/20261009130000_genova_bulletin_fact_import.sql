-- Persist bounded, review-only facts from approved monthly PDF bulletins.
ALTER TABLE public.genova_event_facts
  ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD CONSTRAINT genova_event_facts_source_metadata_object CHECK (
    jsonb_typeof(source_metadata) = 'object'
    AND octet_length(source_metadata::text) <= 16384
  );

-- Bulletin listings share a document URL. Their stable source_uid provides
-- occurrence idempotency, so the URL/time uniqueness rule remains for other
-- sources but does not collapse two listings from the same PDF.
DROP INDEX public.genova_event_facts_occurrence_unique;
CREATE UNIQUE INDEX genova_event_facts_occurrence_unique
  ON public.genova_event_facts (
    feed_id,
    normalized_url,
    COALESCE(start_time, '-infinity'::timestamptz)
  )
  WHERE source_uid NOT LIKE 'genova-bulletin:%';

CREATE FUNCTION public.import_genova_bulletin_facts(
  p_feed_id bigint,
  p_source_page_url text,
  p_bulletin_url text,
  p_retrieved_at timestamptz,
  p_parser_version text,
  p_events jsonb
)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  changed integer;
BEGIN
  PERFORM 1 FROM public.feeds f
    WHERE f.id = p_feed_id AND f.city = 'genova' AND f.status = 'active'
      AND f.url = p_source_page_url
    FOR SHARE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'bulletin import requires the matching active Genova source';
  END IF;
  IF p_bulletin_url IS NULL OR p_bulletin_url !~ '^https://' OR length(p_bulletin_url) > 2048
     OR p_retrieved_at IS NULL OR p_parser_version IS NULL
     OR length(p_parser_version) > 80 THEN
    RAISE EXCEPTION 'invalid bulletin provenance';
  END IF;
  IF jsonb_typeof(p_events) IS DISTINCT FROM 'array' OR jsonb_array_length(p_events) > 500 THEN
    RAISE EXCEPTION 'invalid bulletin event fact array';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(p_events) event
    WHERE event - ARRAY[
      'source_uid', 'title', 'start_time', 'end_time', 'normalized_url',
      'location', 'category_suggestions', 'field_evidence', 'unresolved_reasons',
      'date_precision', 'source_page', 'source_bbox', 'evidence_note',
      'partial_dates', 'start_date_candidate', 'end_date_candidate'
    ]::text[] <> '{}'::jsonb
      OR event ->> 'source_uid' NOT LIKE 'genova-bulletin:%'
      OR length(event ->> 'source_uid') > 100
      OR event ->> 'title' IS NULL OR btrim(event ->> 'title') = '' OR length(event ->> 'title') > 300
      OR event ->> 'normalized_url' IS DISTINCT FROM p_bulletin_url
      OR (event ->> 'start_time' IS NOT NULL AND event ->> 'start_time' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$')
      OR (event ->> 'end_time' IS NOT NULL AND event ->> 'end_time' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$')
      OR COALESCE(jsonb_typeof(event -> 'field_evidence'), 'null') <> 'object'
      OR octet_length(COALESCE(event -> 'field_evidence', '{}'::jsonb)::text) > 8192
      OR COALESCE(jsonb_typeof(event -> 'unresolved_reasons'), 'null') <> 'array'
      OR jsonb_array_length(COALESCE(event -> 'unresolved_reasons', '[]'::jsonb)) > 12
      OR EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(event -> 'unresolved_reasons', '[]'::jsonb)) reason
        WHERE jsonb_typeof(reason) <> 'string' OR length(reason #>> '{}') > 160)
      OR COALESCE(jsonb_typeof(event -> 'partial_dates'), 'null') <> 'array'
      OR jsonb_array_length(COALESCE(event -> 'partial_dates', '[]'::jsonb)) > 31
      OR COALESCE(event ->> 'date_precision', '') NOT IN
        ('day', 'range', 'end_only', 'weekday_only', 'unknown', 'yearless', 'unresolved', 'listed_dates')
      OR ((event ->> 'start_date_candidate') IS NOT NULL AND (event ->> 'start_date_candidate') !~ '^20[0-9]{2}-[0-9]{2}-[0-9]{2}$')
      OR ((event ->> 'end_date_candidate') IS NOT NULL AND (event ->> 'end_date_candidate') !~ '^20[0-9]{2}-[0-9]{2}-[0-9]{2}$')
      OR COALESCE((event ->> 'source_page')::integer, 0) < 1
      OR jsonb_typeof(event -> 'source_bbox') IS DISTINCT FROM 'array'
      OR jsonb_array_length(COALESCE(event -> 'source_bbox', '[]'::jsonb)) <> 4
      OR EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(event -> 'source_bbox', '[]'::jsonb)) bound
        WHERE jsonb_typeof(bound) <> 'number')
      OR EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(event -> 'partial_dates', '[]'::jsonb)) partial
        WHERE jsonb_typeof(partial) <> 'object'
          OR COALESCE((partial ->> 'day')::integer, 0) NOT BETWEEN 1 AND 31
          OR COALESCE((partial ->> 'month')::integer, 0) NOT BETWEEN 1 AND 12)
      OR (event ? 'evidence_note' AND length(event ->> 'evidence_note') > 240)
      OR (event ? 'location' AND length(event ->> 'location') > 240)
      OR (event ? 'category_suggestions' AND jsonb_typeof(event -> 'category_suggestions') IS DISTINCT FROM 'array')
      OR jsonb_array_length(COALESCE(event -> 'category_suggestions', '[]'::jsonb)) > 3
  ) THEN
    RAISE EXCEPTION 'bulletin event facts do not match the bounded review contract';
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
    RAISE EXCEPTION 'invalid bulletin category suggestion';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(p_events) event
    GROUP BY event ->> 'source_uid'
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'bulletin payload contains duplicate candidate identities';
  END IF;
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  INSERT INTO public.genova_event_facts (
    feed_id, source_uid, title, start_time, end_time, is_all_day, location,
    publisher_label, direct_url, normalized_url, category_suggestions,
    review_status, evidence_note, source_metadata
  )
  SELECT p_feed_id, event ->> 'source_uid', event ->> 'title',
    NULLIF(event ->> 'start_time', '')::timestamptz,
    NULLIF(event ->> 'end_time', '')::timestamptz,
    false, NULLIF(event ->> 'location', ''), feed.name, p_bulletin_url,
    event ->> 'normalized_url', COALESCE(event -> 'category_suggestions', '[]'::jsonb),
    'needs_review', NULLIF(event ->> 'evidence_note', ''),
    jsonb_build_object(
      'kind', 'monthly_bulletin_pdf',
      'bulletin_url', p_bulletin_url,
      'retrieved_at', p_retrieved_at,
      'parser_version', p_parser_version,
      'source_page', (event ->> 'source_page')::integer,
      'source_bbox', event -> 'source_bbox',
      'field_evidence', event -> 'field_evidence',
      'unresolved_reasons', event -> 'unresolved_reasons',
      'date_precision', event ->> 'date_precision',
      'start_date_candidate', event ->> 'start_date_candidate',
      'end_date_candidate', event ->> 'end_date_candidate',
      'partial_dates', event -> 'partial_dates'
    )
  FROM jsonb_array_elements(p_events) event
  JOIN public.feeds feed ON feed.id = p_feed_id
  WHERE public.genova_occurrence_is_current(
      NULLIF(event ->> 'start_time', '')::timestamptz,
      NULLIF(event ->> 'end_time', '')::timestamptz,
      false
    )
  ON CONFLICT (source_uid) DO UPDATE SET
    title = EXCLUDED.title,
    start_time = COALESCE(EXCLUDED.start_time, public.genova_event_facts.start_time),
    end_time = COALESCE(EXCLUDED.end_time, public.genova_event_facts.end_time),
    location = COALESCE(EXCLUDED.location, public.genova_event_facts.location),
    direct_url = EXCLUDED.direct_url,
    category_suggestions = EXCLUDED.category_suggestions,
    evidence_note = EXCLUDED.evidence_note,
    source_metadata = EXCLUDED.source_metadata,
    last_seen = now()
  WHERE public.genova_event_facts.feed_id = EXCLUDED.feed_id
    AND public.genova_event_facts.normalized_url = EXCLUDED.normalized_url
    AND public.genova_event_facts.review_status = 'needs_review'
    AND public.genova_event_facts.superseded_by IS NULL;
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed;
END;
$$;

REVOKE ALL ON FUNCTION public.import_genova_bulletin_facts(bigint,text,text,timestamptz,text,jsonb)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.import_genova_bulletin_facts(bigint,text,text,timestamptz,text,jsonb)
  TO service_role;
