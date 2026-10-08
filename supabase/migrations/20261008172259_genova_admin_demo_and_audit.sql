-- #86: browser-managed private event corrections/audit and an isolated public demo set.
ALTER TABLE public.genova_event_facts
  ADD COLUMN tags text[] NOT NULL DEFAULT '{}';

REVOKE UPDATE ON TABLE public.genova_event_facts FROM authenticated;
GRANT UPDATE (title, start_time, end_time, location, direct_url, normalized_url, category,
  category_confidence, tags, review_status, evidence_note)
  ON TABLE public.genova_event_facts TO authenticated;

CREATE OR REPLACE FUNCTION public.guard_genova_event_publication()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
  IF NEW.review_status = 'published' THEN
    IF NEW.start_time IS NULL THEN
      RAISE EXCEPTION 'published Genova events require a start time';
    END IF;
    IF NEW.title IS NULL OR btrim(NEW.title) = ''
      OR NEW.location IS NULL OR btrim(NEW.location) = ''
      OR NEW.category IS NULL OR btrim(NEW.category) = ''
      OR NEW.direct_url IS NULL OR btrim(NEW.direct_url) = '' THEN
      RAISE EXCEPTION 'published Genova events require title, location, category, and source link';
    END IF;
    IF TG_OP = 'INSERT' OR OLD.review_status NOT IN ('validated', 'published') THEN
      RAISE EXCEPTION 'Genova events must be validated before publication';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM public.feeds f
      WHERE f.id = NEW.feed_id AND f.city = 'genova' AND f.status = 'active'
    ) THEN
      RAISE EXCEPTION 'published Genova events require an active approved source';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS genova_event_publication_guard ON public.genova_event_facts;
CREATE TRIGGER genova_event_publication_guard
BEFORE INSERT OR UPDATE OF review_status, start_time, feed_id, title, location, category, direct_url
ON public.genova_event_facts
FOR EACH ROW EXECUTE FUNCTION public.guard_genova_event_publication();

CREATE TABLE public.genova_event_fact_audit (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_fact_id bigint REFERENCES public.genova_event_facts(id) ON DELETE SET NULL,
  source_uid text NOT NULL,
  changed_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  changed_at timestamptz NOT NULL DEFAULT now(),
  old_values jsonb NOT NULL,
  new_values jsonb NOT NULL
);
ALTER TABLE public.genova_event_fact_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_event_fact_audit FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.genova_event_fact_audit TO authenticated;
GRANT ALL ON TABLE public.genova_event_fact_audit TO service_role;
CREATE POLICY "Admins can view Genova event audit"
  ON public.genova_event_fact_audit FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.admin_users WHERE user_id = (SELECT auth.uid())));

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
      'location', OLD.location, 'direct_url', OLD.direct_url, 'normalized_url', OLD.normalized_url, 'category', OLD.category,
      'category_confidence', OLD.category_confidence, 'tags', OLD.tags,
      'review_status', OLD.review_status, 'evidence_note', OLD.evidence_note
    ),
    jsonb_build_object(
      'title', NEW.title, 'start_time', NEW.start_time, 'end_time', NEW.end_time,
      'location', NEW.location, 'direct_url', NEW.direct_url, 'normalized_url', NEW.normalized_url, 'category', NEW.category,
      'category_confidence', NEW.category_confidence, 'tags', NEW.tags,
      'review_status', NEW.review_status, 'evidence_note', NEW.evidence_note
    )
  );
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.audit_genova_event_fact_change() FROM PUBLIC, anon, authenticated;
CREATE TRIGGER genova_event_fact_audit_update
AFTER UPDATE ON public.genova_event_facts
FOR EACH ROW WHEN (
  OLD.title IS DISTINCT FROM NEW.title OR OLD.start_time IS DISTINCT FROM NEW.start_time
  OR OLD.end_time IS DISTINCT FROM NEW.end_time OR OLD.location IS DISTINCT FROM NEW.location
  OR OLD.direct_url IS DISTINCT FROM NEW.direct_url OR OLD.normalized_url IS DISTINCT FROM NEW.normalized_url
  OR OLD.category IS DISTINCT FROM NEW.category
  OR OLD.category_confidence IS DISTINCT FROM NEW.category_confidence OR OLD.tags IS DISTINCT FROM NEW.tags
  OR OLD.review_status IS DISTINCT FROM NEW.review_status OR OLD.evidence_note IS DISTINCT FROM NEW.evidence_note
) EXECUTE FUNCTION public.audit_genova_event_fact_change();

CREATE TABLE public.genova_demo_events (
  id text PRIMARY KEY CHECK (id ~ '^sample-[a-z0-9-]+$'),
  title text NOT NULL CHECK (btrim(title) <> ''),
  category text NOT NULL,
  categories text[] NOT NULL,
  days_from_today integer NOT NULL CHECK (days_from_today BETWEEN 0 AND 60),
  start_time text CHECK (start_time IS NULL OR start_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
  venue text NOT NULL CHECK (btrim(venue) <> ''),
  source_name text NOT NULL CHECK (btrim(source_name) <> ''),
  source_url text NOT NULL CHECK (source_url ~ '^https://(www\.)?example\.org(/|$)'),
  tags text[] NOT NULL DEFAULT '{}',
  CHECK (category = ANY(categories)),
  CHECK (categories <@ ARRAY['music','theatre-performance','art-exhibitions','sports','food-drink','festivals-markets','talks-workshops','family','outdoors-tours','community-social']::text[]),
  CHECK (tags <@ ARRAY['date-night']::text[])
);
ALTER TABLE public.genova_demo_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.genova_demo_events FROM PUBLIC, anon, authenticated;
GRANT ALL ON TABLE public.genova_demo_events TO service_role;

CREATE OR REPLACE FUNCTION public.list_genova_demo_events()
RETURNS TABLE (
  id text, title text, category text, categories text[],
  "daysFromToday" integer, "startTime" text, venue text,
  "sourceName" text, "sourceUrl" text, tags text[]
) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
  SELECT d.id, d.title, d.category, d.categories, d.days_from_today,
    d.start_time, d.venue, d.source_name, d.source_url, d.tags
  FROM public.genova_demo_events AS d
  ORDER BY d.days_from_today, d.start_time NULLS LAST, d.id
$$;
REVOKE ALL ON FUNCTION public.list_genova_demo_events() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.list_genova_demo_events() TO anon, authenticated, service_role;

CREATE OR REPLACE FUNCTION public.replace_genova_demo_events(p_events jsonb)
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  inserted_count integer;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'admin access required' USING ERRCODE = '42501';
  END IF;
  IF jsonb_typeof(p_events) IS DISTINCT FROM 'array' OR jsonb_array_length(p_events) > 100 THEN
    RAISE EXCEPTION 'demo events must be an array with at most 100 rows' USING ERRCODE = '22023';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_array_elements(p_events) AS e
    WHERE jsonb_typeof(e) <> 'object'
      OR COALESCE(e->>'id','') !~ '^sample-[a-z0-9-]+$'
      OR COALESCE(btrim(e->>'title'),'') = ''
      OR COALESCE(btrim(e->>'venue'),'') = ''
      OR COALESCE(btrim(e->>'sourceName'),'') = ''
      OR COALESCE(e->>'sourceUrl','') !~ '^https://(www\.)?example\.org(/|$)'
      OR COALESCE(e->>'daysFromToday','') !~ '^(0|[1-9][0-9]?)$'
      OR (e->>'daysFromToday')::integer > 60
      OR (e->>'startTime' IS NOT NULL AND e->>'startTime' <> 'null'
        AND e->>'startTime' !~ '^([01][0-9]|2[0-3]):[0-5][0-9]$')
      OR COALESCE(jsonb_typeof(e->'tags'),'array') <> 'array'
      OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(e->'tags','[]'::jsonb)) AS tag WHERE tag <> 'date-night')
      OR COALESCE(jsonb_typeof(e->'categories'),'array') <> 'array'
      OR NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(e->'categories', jsonb_build_array(e->>'category'))) AS cat WHERE cat = e->>'category')
      OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(COALESCE(e->'categories', jsonb_build_array(e->>'category'))) AS cat
        WHERE cat NOT IN ('music','theatre-performance','art-exhibitions','sports','food-drink','festivals-markets','talks-workshops','family','outdoors-tours','community-social'))
  ) OR (SELECT count(*) <> count(DISTINCT e->>'id') FROM jsonb_array_elements(p_events) AS e) THEN
    RAISE EXCEPTION 'demo event fields are invalid' USING ERRCODE = '22023';
  END IF;
  DELETE FROM public.genova_demo_events;
  INSERT INTO public.genova_demo_events (
    id,title,category,categories,days_from_today,start_time,venue,source_name,source_url,tags
  )
  SELECT e->>'id', e->>'title', e->>'category',
    COALESCE(ARRAY(SELECT jsonb_array_elements_text(e->'categories')), ARRAY[e->>'category']),
    (e->>'daysFromToday')::integer, NULLIF(e->>'startTime','null'), e->>'venue',
    e->>'sourceName', e->>'sourceUrl',
    COALESCE(ARRAY(SELECT jsonb_array_elements_text(e->'tags')), ARRAY[]::text[])
  FROM jsonb_array_elements(p_events) AS e;
  GET DIAGNOSTICS inserted_count = ROW_COUNT;
  RETURN inserted_count;
END;
$$;
REVOKE ALL ON FUNCTION public.replace_genova_demo_events(jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.replace_genova_demo_events(jsonb) TO authenticated;

CREATE OR REPLACE FUNCTION public.clear_genova_demo_events()
RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE deleted_count integer;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'admin access required' USING ERRCODE = '42501';
  END IF;
  DELETE FROM public.genova_demo_events;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$;
REVOKE ALL ON FUNCTION public.clear_genova_demo_events() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.clear_genova_demo_events() TO authenticated;

-- The public preview starts with its existing fictional fixture set.
INSERT INTO public.genova_demo_events (id,title,category,categories,days_from_today,start_time,venue,source_name,source_url,tags)
SELECT e->>'id',e->>'title',e->>'category',COALESCE(ARRAY(SELECT jsonb_array_elements_text(e->'categories')),ARRAY[e->>'category']),
(e->>'daysFromToday')::integer,NULLIF(e->>'startTime','null'),e->>'venue',e->>'sourceName',e->>'sourceUrl',
COALESCE(ARRAY(SELECT jsonb_array_elements_text(e->'tags')),ARRAY[]::text[])
FROM jsonb_array_elements($sample_events$[
  {
    "id": "sample-food-workshop",
    "title": "Make fresh pesto together",
    "category": "food-drink",
    "daysFromToday": 1,
    "startTime": "18:30",
    "venue": "Example neighbourhood kitchen, Genova",
    "sourceName": "Example Community Kitchen",
    "sourceUrl": "https://example.org/genova/pesto-workshop",
    "tags": []
  },
  {
    "id": "sample-jazz-evening",
    "title": "Jazz at the harbour",
    "category": "music",
    "daysFromToday": 3,
    "startTime": "20:00",
    "venue": "Example music room, Genova",
    "sourceName": "Example Local Venue",
    "sourceUrl": "https://example.org/genova/jazz",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-gallery-evening",
    "title": "An evening with Ligurian artists",
    "category": "art-exhibitions",
    "daysFromToday": 4,
    "startTime": null,
    "venue": "Example gallery, Genova",
    "sourceName": "Example Arts Publisher",
    "sourceUrl": "https://example.org/genova/art-evening",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-theatre",
    "title": "A comedy in the old town",
    "category": "theatre-performance",
    "daysFromToday": 5,
    "startTime": "21:00",
    "venue": "Example theatre, Genova",
    "sourceName": "Example Theatre Company",
    "sourceUrl": "https://example.org/genova/comedy",
    "tags": []
  },
  {
    "id": "sample-volleyball",
    "title": "Community volleyball match",
    "category": "sports",
    "daysFromToday": 6,
    "startTime": "17:00",
    "venue": "Example sports court, Genova",
    "sourceName": "Example Sports Club",
    "sourceUrl": "https://example.org/genova/volleyball",
    "tags": []
  },
  {
    "id": "sample-walk",
    "title": "A coastal walk and aperitivo",
    "category": "outdoors-tours",
    "daysFromToday": 8,
    "startTime": "16:00",
    "venue": "Example meeting point, Genova",
    "sourceName": "Example Outdoor Group",
    "sourceUrl": "https://example.org/genova/coastal-walk",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-jazz-quartet",
    "title": "Jazz quartet at the old port",
    "category": "music",
    "categories": [
      "music",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "18:00",
    "venue": "Example port stage, Genova",
    "sourceName": "Example Music Calendar",
    "sourceUrl": "https://example.org/genova/jazz-quartet",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-acoustic-set",
    "title": "Acoustic songs and sunset views",
    "category": "music",
    "categories": [
      "music"
    ],
    "daysFromToday": 4,
    "startTime": "18:45",
    "venue": "Example seaside terrace, Genova",
    "sourceName": "Example Local Venue",
    "sourceUrl": "https://example.org/genova/acoustic-sunset",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-theatre-improv",
    "title": "Improv comedy in English and Italian",
    "category": "theatre-performance",
    "categories": [
      "theatre-performance",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "19:00",
    "venue": "Example black box theatre, Genova",
    "sourceName": "Example Theatre Company",
    "sourceUrl": "https://example.org/genova/improv-night",
    "tags": []
  },
  {
    "id": "sample-pasta-class",
    "title": "A hands-on Ligurian pasta class",
    "category": "food-drink",
    "categories": [
      "food-drink",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "19:15",
    "venue": "Example cooking studio, Genova",
    "sourceName": "Example Community Kitchen",
    "sourceUrl": "https://example.org/genova/pasta-class",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-gallery-opening",
    "title": "Opening night: new Ligurian art",
    "category": "art-exhibitions",
    "categories": [
      "art-exhibitions",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "19:30",
    "venue": "Example art space, Genova",
    "sourceName": "Example Arts Publisher",
    "sourceUrl": "https://example.org/genova/gallery-opening",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-board-games",
    "title": "Board games for new neighbours",
    "category": "community-social",
    "categories": [
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "19:45",
    "venue": "Example community room, Genova",
    "sourceName": "Example Social Club",
    "sourceUrl": "https://example.org/genova/board-games",
    "tags": []
  },
  {
    "id": "sample-street-photo-walk",
    "title": "Street photography walk through the caruggi",
    "category": "art-exhibitions",
    "categories": [
      "art-exhibitions",
      "outdoors-tours"
    ],
    "daysFromToday": 4,
    "startTime": "20:00",
    "venue": "Example meeting point, Genova",
    "sourceName": "Example Photo Collective",
    "sourceUrl": "https://example.org/genova/photo-walk",
    "tags": []
  },
  {
    "id": "sample-five-a-side",
    "title": "Friendly five-a-side football",
    "category": "sports",
    "categories": [
      "sports",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "20:15",
    "venue": "Example sports centre, Genova",
    "sourceName": "Example Sports Club",
    "sourceUrl": "https://example.org/genova/five-a-side",
    "tags": []
  },
  {
    "id": "sample-film-screening",
    "title": "Outdoor film: stories of the sea",
    "category": "art-exhibitions",
    "categories": [
      "art-exhibitions",
      "outdoors-tours"
    ],
    "daysFromToday": 4,
    "startTime": "20:30",
    "venue": "Example courtyard cinema, Genova",
    "sourceName": "Example Film Society",
    "sourceUrl": "https://example.org/genova/sea-film",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-trivia",
    "title": "Pub quiz: Liguria edition",
    "category": "community-social",
    "categories": [
      "community-social",
      "food-drink"
    ],
    "daysFromToday": 4,
    "startTime": "20:45",
    "venue": "Example neighbourhood pub, Genova",
    "sourceName": "Example Pub Events",
    "sourceUrl": "https://example.org/genova/liguria-quiz",
    "tags": []
  },
  {
    "id": "sample-dance-class",
    "title": "Beginner salsa social",
    "category": "community-social",
    "categories": [
      "community-social",
      "music"
    ],
    "daysFromToday": 4,
    "startTime": "21:00",
    "venue": "Example dance studio, Genova",
    "sourceName": "Example Dance School",
    "sourceUrl": "https://example.org/genova/salsa-social",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-poetry",
    "title": "Open mic poetry and spoken word",
    "category": "theatre-performance",
    "categories": [
      "theatre-performance",
      "community-social"
    ],
    "daysFromToday": 4,
    "startTime": "21:15",
    "venue": "Example bookshop stage, Genova",
    "sourceName": "Example Bookshop Events",
    "sourceUrl": "https://example.org/genova/open-mic",
    "tags": []
  },
  {
    "id": "sample-basketball",
    "title": "Local basketball derby",
    "category": "sports",
    "categories": [
      "sports"
    ],
    "daysFromToday": 4,
    "startTime": "21:30",
    "venue": "Example arena, Genova",
    "sourceName": "Example Basketball Club",
    "sourceUrl": "https://example.org/genova/basketball-derby",
    "tags": []
  },
  {
    "id": "sample-aperitivo-walk",
    "title": "Aperitivo walk above the harbour",
    "category": "outdoors-tours",
    "categories": [
      "outdoors-tours",
      "food-drink"
    ],
    "daysFromToday": 4,
    "startTime": "21:45",
    "venue": "Example lookout, Genova",
    "sourceName": "Example Walking Group",
    "sourceUrl": "https://example.org/genova/aperitivo-walk",
    "tags": [
      "date-night"
    ]
  },
  {
    "id": "sample-improv-late-show",
    "title": "Late-night improv show",
    "category": "theatre-performance",
    "categories": [
      "theatre-performance"
    ],
    "daysFromToday": 4,
    "startTime": "22:00",
    "venue": "Example theatre, Genova",
    "sourceName": "Example Theatre Company",
    "sourceUrl": "https://example.org/genova/improv-late-show",
    "tags": []
  },
  {
    "id": "sample-genova-market",
    "title": "Example makers and neighbourhood market",
    "category": "festivals-markets",
    "categories": [
      "festivals-markets",
      "art-exhibitions"
    ],
    "daysFromToday": 9,
    "startTime": "10:00",
    "venue": "Example market square, Genova",
    "sourceName": "Example Community Market",
    "sourceUrl": "https://example.org/genova/market",
    "tags": []
  },
  {
    "id": "sample-public-talk",
    "title": "Example talk about the Ligurian coast",
    "category": "talks-workshops",
    "daysFromToday": 10,
    "startTime": "18:00",
    "venue": "Example local library, Genova",
    "sourceName": "Example Local Library",
    "sourceUrl": "https://example.org/genova/coast-talk",
    "tags": []
  },
  {
    "id": "sample-family-workshop",
    "title": "Example family art workshop",
    "category": "family",
    "categories": [
      "family",
      "talks-workshops",
      "art-exhibitions"
    ],
    "daysFromToday": 11,
    "startTime": "15:00",
    "venue": "Example family centre, Genova",
    "sourceName": "Example Family Centre",
    "sourceUrl": "https://example.org/genova/family-workshop",
    "tags": []
  }
]
$sample_events$::jsonb) AS e;
