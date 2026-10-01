-- Keep source candidates reviewable without exposing their notes publicly.
-- Collection scripts already select only status='active'.
ALTER TABLE public.feeds
  DROP CONSTRAINT IF EXISTS feeds_status_check;

ALTER TABLE public.feeds
  ADD CONSTRAINT feeds_status_check
  CHECK (status IN ('active', 'pending', 'paused', 'rejected', 'removed'));

ALTER TABLE public.feeds
  ADD COLUMN IF NOT EXISTS publisher_url text,
  ADD COLUMN IF NOT EXISTS discovery_method text NOT NULL DEFAULT 'manual';

ALTER TABLE public.feeds
  DROP CONSTRAINT IF EXISTS feeds_discovery_method_check,
  ADD CONSTRAINT feeds_discovery_method_check
    CHECK (discovery_method IN ('manual', 'ics', 'scraper', 'api', 'agent'));

CREATE TABLE IF NOT EXISTS public.feed_source_reviews (
  city text NOT NULL,
  feed_url text NOT NULL,
  source_provenance text,
  access_notes text,
  genova_fit text NOT NULL DEFAULT 'unknown'
    CHECK (genova_fit IN ('confirmed', 'likely', 'unknown', 'out_of_scope')),
  discovery_reason text,
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (city, feed_url),
  FOREIGN KEY (city, feed_url)
    REFERENCES public.feeds(city, url) ON DELETE CASCADE
);

ALTER TABLE public.feed_source_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.feed_source_reviews FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.feed_source_reviews TO authenticated;
GRANT ALL ON public.feed_source_reviews TO service_role;
DROP POLICY IF EXISTS "Admin users can manage feed source reviews" ON public.feed_source_reviews;
CREATE POLICY "Admin users can manage feed source reviews"
  ON public.feed_source_reviews FOR ALL TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM public.admin_users))
  WITH CHECK (auth.uid() IN (SELECT user_id FROM public.admin_users));

DROP POLICY IF EXISTS "Anyone can read feeds" ON public.feeds;
DROP POLICY IF EXISTS "Public can read active feeds" ON public.feeds;
CREATE POLICY "Public can read active feeds"
  ON public.feeds FOR SELECT TO anon, authenticated
  USING (status = 'active');

DROP POLICY IF EXISTS "Admin users can manage feeds" ON public.feeds;
CREATE POLICY "Admin users can manage feeds"
  ON public.feeds FOR ALL TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM public.admin_users))
  WITH CHECK (auth.uid() IN (SELECT user_id FROM public.admin_users));

-- remove_feed is SECURITY DEFINER, so it must enforce admin authorization
-- inside the function rather than relying on table RLS.
CREATE OR REPLACE FUNCTION public.remove_feed(feed_id bigint)
RETURNS TABLE (events_deleted bigint, feed_deleted boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  f record;
  ev_count bigint;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'remove_feed: admin access required' USING ERRCODE = '42501';
  END IF;

  SELECT city, name INTO f FROM public.feeds WHERE id = feed_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'remove_feed: no feed row with id %', feed_id;
  END IF;

  DELETE FROM public.events e WHERE e.city = f.city AND e.source = f.name;
  GET DIAGNOSTICS ev_count = ROW_COUNT;

  DELETE FROM public.feeds WHERE id = feed_id;
  RETURN QUERY SELECT ev_count, true;
END;
$$;

REVOKE ALL ON FUNCTION public.remove_feed(bigint) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.remove_feed(bigint) TO authenticated;

-- Rejected rows are retained for review history even when their scraper
-- proposal is malformed. Re-activating a scraper still re-runs validation.
CREATE OR REPLACE FUNCTION public.validate_scraper_row()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.feed_type = 'scraper' AND coalesce(NEW.status, 'active') NOT IN ('removed', 'rejected') THEN
    IF NEW.url IS NULL OR NEW.url !~ '^cities/[a-z0-9-]+/[A-Za-z0-9._-]+\.ics$' THEN
      RAISE EXCEPTION
        'scraper row rejected: url must be an output path like cities/<city>/<file>.ics, got %',
        coalesce(NEW.url, '<null>');
    END IF;
    IF NEW.scraper_cmd IS NULL OR btrim(NEW.scraper_cmd) = '' THEN
      RAISE EXCEPTION
        'scraper row rejected: scraper_cmd is required for non-removed scraper rows (url %)',
        NEW.url;
    END IF;
    IF NEW.scraper_cmd !~ '^python (scrapers|scripts)/' THEN
      RAISE EXCEPTION
        'scraper row rejected: scraper_cmd must start with "python scrapers/" or "python scripts/", got %',
        left(NEW.scraper_cmd, 80);
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
