-- Retain source placeholders as private audit rows rather than deleting history.
ALTER TABLE public.genova_event_facts
  ADD COLUMN superseded_by bigint REFERENCES public.genova_event_facts(id) ON DELETE RESTRICT,
  ADD COLUMN superseded_at timestamptz,
  ADD CONSTRAINT genova_event_supersession_state CHECK (
    (superseded_by IS NULL AND superseded_at IS NULL) OR
    (superseded_by IS NOT NULL AND superseded_by <> id AND superseded_at IS NOT NULL
      AND start_time IS NULL AND review_status = 'needs_review')
  );
CREATE INDEX genova_event_superseded_by_idx ON public.genova_event_facts(superseded_by)
  WHERE superseded_by IS NOT NULL;

-- The browser can review/correct facts but cannot edit source identity or audit links.
REVOKE UPDATE ON public.genova_event_facts FROM authenticated;
GRANT UPDATE (title, start_time, end_time, location, category, category_confidence,
  review_status, evidence_note) ON public.genova_event_facts TO authenticated;
ALTER POLICY "Admins can update Genova event facts" ON public.genova_event_facts
  USING (superseded_by IS NULL AND EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = (SELECT auth.uid())
  ))
  WITH CHECK (superseded_by IS NULL AND EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = (SELECT auth.uid())
  ));

CREATE FUNCTION public.guard_genova_event_supersession()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
  IF NEW.superseded_by IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.genova_event_facts target
    WHERE target.id = NEW.superseded_by AND target.feed_id = NEW.feed_id
      AND target.normalized_url = NEW.normalized_url AND target.start_time IS NOT NULL
      AND target.superseded_by IS NULL
  ) THEN
    RAISE EXCEPTION 'supersession requires a dated occurrence of the same source URL';
  END IF;
  IF NEW.start_time IS NULL AND EXISTS (
    SELECT 1 FROM public.genova_event_facts placeholder WHERE placeholder.superseded_by = NEW.id
  ) THEN
    RAISE EXCEPTION 'a supersession target must retain its known start time';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER genova_event_supersession_guard BEFORE INSERT OR UPDATE
  ON public.genova_event_facts FOR EACH ROW EXECUTE FUNCTION public.guard_genova_event_supersession();
REVOKE ALL ON FUNCTION public.guard_genova_event_supersession() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.guard_genova_event_supersession() TO service_role;

CREATE FUNCTION public.reconcile_genova_event_placeholders(p_feed_id bigint, p_urls text[])
RETURNS integer LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE changed integer;
BEGIN
  -- Serialize the trusted import/repair path; no source requests or publication.
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  UPDATE public.genova_event_facts placeholder
  SET superseded_by = target.id, superseded_at = now()
  FROM public.genova_event_facts target, public.feeds f
  WHERE f.id = p_feed_id AND f.city = 'genova' AND f.status = 'active'
    AND placeholder.feed_id = f.id AND target.feed_id = f.id
    AND placeholder.normalized_url = ANY(p_urls)
    AND target.normalized_url = placeholder.normalized_url
    AND lower(btrim(target.title)) = lower(btrim(placeholder.title))
    AND placeholder.start_time IS NULL AND placeholder.review_status = 'needs_review'
    AND placeholder.superseded_by IS NULL AND target.start_time IS NOT NULL
    AND target.superseded_by IS NULL
    AND placeholder.source_uid LIKE 'genova-luzzati:%'
    AND target.source_uid LIKE 'genova-luzzati:%'
    AND (SELECT count(*) FROM public.genova_event_facts occurrence
      WHERE occurrence.feed_id = f.id AND occurrence.normalized_url = target.normalized_url
        AND occurrence.start_time IS NOT NULL) = 1;
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed;
END;
$$;
REVOKE ALL ON FUNCTION public.reconcile_genova_event_placeholders(bigint,text[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reconcile_genova_event_placeholders(bigint,text[]) TO service_role;

CREATE FUNCTION public.import_genova_luzzati_facts(p_feed_id bigint, p_events jsonb)
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
  LOCK TABLE public.genova_event_facts IN SHARE ROW EXCLUSIVE MODE;
  INSERT INTO public.genova_event_facts (
    feed_id, source_uid, title, start_time, end_time, location, publisher_label,
    direct_url, normalized_url, category, category_confidence, review_status, evidence_note
  )
  SELECT p_feed_id, event ->> 'source_uid', event ->> 'title',
    NULLIF(event ->> 'start_time','')::timestamptz,
    NULLIF(event ->> 'end_time','')::timestamptz, NULLIF(event ->> 'location',''),
    event ->> 'publisher', event ->> 'url', event ->> 'normalized_url',
    NULLIF(event ->> 'category',''), NULLIF(event ->> 'category_confidence','')::numeric,
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
    last_seen = now(), evidence_note = EXCLUDED.evidence_note
  WHERE public.genova_event_facts.feed_id = EXCLUDED.feed_id
    AND public.genova_event_facts.normalized_url = EXCLUDED.normalized_url
    AND public.genova_event_facts.review_status = 'needs_review'
    AND public.genova_event_facts.superseded_by IS NULL;
  GET DIAGNOSTICS changed = ROW_COUNT;
  -- Only a report with exactly one dated occurrence and no undated candidate
  -- supports automatic supersession. Shared-URL series remain reviewable.
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

-- Repair the inspected pending pairs using the same conservative rule. Retain
-- both row IDs, source UIDs, timestamps, evidence, and needs_review state.
SELECT public.reconcile_genova_event_placeholders(f.id, ARRAY(
  SELECT DISTINCT normalized_url FROM public.genova_event_facts WHERE feed_id = f.id
)) FROM public.feeds f WHERE city = 'genova' AND status = 'active'
  AND url = 'https://www.spazio-comune.org/categoria-prodotto/eventi/';
