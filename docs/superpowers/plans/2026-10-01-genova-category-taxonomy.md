# Genova Category Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Give the Genova preview and event-normalization code one shared, reviewable category vocabulary.

**Architecture:** `genova-taxonomy.json` is the canonical list of public keys, labels, inherited classifier mappings, exclusions, and the Date night tag. Python normalization preserves source labels and review status; the browser loads the same JSON for filters and fixture validation. Category feed generation and publishing stay in issue #1.

**Tech Stack:** JSON, browser JavaScript, Python, Node's built-in test runner, pytest in CI.

**Spec:** `PROJECT_SCOPE.md`; GitHub issue #15.

## Global Constraints

- Public calendar use stays free and account-free.
- Use the ten Genova categories in `PROJECT_SCOPE.md` and `Europe/Rome` dates.
- Keep Date night as a tag; retain unknown or uncertain classification for review.
- Do not connect inherited backend credentials or claim live events or feeds.

## Review Focus

- An inherited label is unmapped: retain it and mark it for review.
- A classification has no confidence or is below 0.75: keep it reviewable.
- Government / Civic is intentionally excluded: preserve the source label and explicit exclusion status.
- A multi-category event is filtered by any selected category.
- Date night must not become a public category.

---

### Task 1: Define and normalize the taxonomy

**Files:**
- Create `genova-taxonomy.json` with stable category keys, labels, all inherited mappings, the `date-night` tag, the `Government / Civic` exclusion, and the 0.75 review threshold.
- Create `scripts/genova_taxonomy.py` with `normalize_genova_event(event) -> dict`.
- Create `tests/test_genova_taxonomy.py`.

**Interfaces:** The normalizer consumes legacy `category`, optional `categories`, optional `classification_confidence`, and `tags`; it returns public `category`/`categories`, preserves `source_category_labels`, and reports `classification_review.status` as `ready`, `review`, or `excluded`.

- [x] Write tests proving inherited labels are all mapped or explicitly excluded; multi-category mapping is stable; date-night remains a tag; unknown, missing-confidence, and low-confidence inputs stay reviewable; known exclusions remain visible.
- [x] Run `python3 -m pytest tests/test_genova_taxonomy.py -v`.
- [x] Implement taxonomy and normalizer.
- [x] Run `python3 -m pytest tests/test_genova_taxonomy.py -v`.

### Task 2: Use the taxonomy in the preview

**Files:**
- Modify `xmlui/sample-preview.js` to load the shared JSON in browsers and consume the same file in Node tests.
- Modify `xmlui/genova-sample-preview.html` and `xmlui/sample-preview.css` to render filters from taxonomy entries.
- Update `xmlui/sample-events.json` so fixtures use public keys and include each public category.
- Extend `tests/sample-preview.test.js` for dynamic filters, category labels, and sample coverage.

**Interfaces:** Browser loader fetches `../genova-taxonomy.json`; event fixtures use a primary `category`, optional multi-value `categories`, and separate `tags`.

- [x] Add tests for taxonomy-driven labels and filters, browser JSON path, multi-category matches, and tag validation.
- [x] Run `node --test tests/sample-preview.test.js`.
- [x] Implement dynamic filters and migrate fixtures.
- [x] Run `node --test tests/sample-preview.test.js`.

### Task 3: Document the boundary and verify the branch

**Files:**
- Create `docs/genova-category-taxonomy.md`.
- Add a concise `CHANGELOG.md` entry.
- Keep this plan with the implementation record.

- [x] Run `python3 scripts/check_markdown_links.py`.
- [x] Run `python3 scripts/validate_pr_feeds.py --base-ref origin/main`.
- [x] Run `python3 -m pytest tests/ -v` and `node --test tests/sample-preview.test.js`.
- [x] Run `git diff --check`.
- [x] Complete the fresh branch review; add red-to-green regression tests for malformed boolean confidence and repeated normalization of unknown/excluded labels.
- [ ] Open the PR and wait for GitHub checks.
