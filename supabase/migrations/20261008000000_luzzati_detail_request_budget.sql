-- Issue #87: record and constrain the bounded detail-page pilot budget.
ALTER TABLE public.genova_source_scans
  DROP CONSTRAINT IF EXISTS genova_source_scans_request_count_check;

ALTER TABLE public.genova_source_scans
  ADD CONSTRAINT genova_source_scans_request_count_check
  CHECK (request_count >= 0 AND request_count <= 14);

ALTER TABLE public.genova_source_scans
  ADD COLUMN detail_page_limit integer NOT NULL DEFAULT 0
    CHECK (detail_page_limit >= 0 AND detail_page_limit <= 12),
  ADD COLUMN detail_pages_checked integer NOT NULL DEFAULT 0
    CHECK (detail_pages_checked >= 0 AND detail_pages_checked <= detail_page_limit);

ALTER TABLE public.genova_source_scans
  ADD CONSTRAINT genova_source_scans_luzzati_request_budget_check
  CHECK (request_count = 2 + detail_pages_checked);
