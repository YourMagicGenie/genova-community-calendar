-- feeds: all calendar sources (ICS URLs, scrapers, curators) per city
-- Source of truth for what feeds are in the system.
-- Replaces feeds.txt and pending_feeds.

CREATE TABLE feeds (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  city text NOT NULL,
  url text NOT NULL,
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'pending', 'paused', 'rejected', 'removed')),
  feed_type text NOT NULL CHECK (feed_type IN ('ics_url', 'scraper', 'curator')),
  scraper_cmd text,
  fallback_url text,
  publisher_url text,
  discovery_method text NOT NULL DEFAULT 'manual' CHECK (discovery_method IN ('manual', 'ics', 'scraper', 'api', 'agent')),
  created_at timestamptz DEFAULT now(),
  UNIQUE(city, url)
);

ALTER TABLE feeds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read active feeds" ON feeds FOR SELECT TO anon, authenticated USING (status = 'active');

CREATE POLICY "Admin users can manage feeds" ON feeds FOR ALL
  TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM admin_users))
  WITH CHECK (auth.uid() IN (SELECT user_id FROM admin_users));

-- Used by the Manage Feeds delete button (SECURITY DEFINER bypasses RLS).
-- Atomic since 20260807170000_atomic_remove_feed.sql: deletes the feed's
-- events (matched by the feed's city + name) and the feed row in one
-- transaction, returns what it deleted, and raises for an unknown id.
-- Callers that still pre-delete events by source+city simply leave 0
-- rows for the RPC to delete — backward compatible.
CREATE FUNCTION remove_feed(feed_id bigint)
RETURNS TABLE (events_deleted bigint, feed_deleted boolean)
LANGUAGE plpgsql SECURITY DEFINER
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

-- Insert-time validation for scraper rows
-- (since 20260807171000_insert_time_scraper_validation.sql):
-- a BEFORE INSERT OR UPDATE trigger (feeds_validate_scraper_row →
-- validate_scraper_row()) rejects non-removed scraper rows whose url is
-- not an output path (cities/<city>/<file>.ics — never an http(s) URL),
-- whose scraper_cmd is missing/empty, or whose scraper_cmd does not
-- start with "python scrapers/" or "python scripts/". Removed-status
-- tombstones are exempt. This enforces cleanup-plan item 4 on every
-- write path (Manage Feeds, pending-feeds processing, backfill sync,
-- ad hoc SQL) ahead of DB-first scraper execution.
CREATE OR REPLACE FUNCTION validate_scraper_row()
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

CREATE TRIGGER feeds_validate_scraper_row
BEFORE INSERT OR UPDATE ON feeds
FOR EACH ROW EXECUTE FUNCTION validate_scraper_row();

-- Private source-review notes are separated from the public source inventory:
-- row-level policies alone cannot hide individual columns on active feeds.
CREATE TABLE feed_source_reviews (
  city text NOT NULL,
  feed_url text NOT NULL,
  source_provenance text,
  access_notes text,
  genova_fit text NOT NULL DEFAULT 'unknown' CHECK (genova_fit IN ('confirmed', 'likely', 'unknown', 'out_of_scope')),
  discovery_reason text,
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (city, feed_url),
  FOREIGN KEY (city, feed_url) REFERENCES feeds(city, url) ON DELETE CASCADE
);

ALTER TABLE feed_source_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON feed_source_reviews FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON feed_source_reviews TO authenticated;
GRANT ALL ON feed_source_reviews TO service_role;
CREATE POLICY "Admin users can manage feed source reviews"
  ON feed_source_reviews FOR ALL TO authenticated
  USING (auth.uid() IN (SELECT user_id FROM admin_users))
  WITH CHECK (auth.uid() IN (SELECT user_id FROM admin_users));
