# Inherited data and generated artifact inventory

**Audited:** 2026-10-01  
**Scope:** Issue #18; current default-branch working tree before this cleanup.

This audit separates test/source inputs from upstream-generated files. It does not rewrite public Git history.

## Keep: active code, fixtures, and useful published state

| Path | Current size | Role and consumers | Decision |
| --- | ---: | --- | --- |
| `tests/` | 195,404 bytes across 25 files | Parser, pipeline, database, and Genova preview tests; includes checked-in ICS/HTML fixtures. | Keep. Tests need these inputs. |
| `cities/` | 5,833,936 bytes across 70 files | Inherited scraper code, city configuration, and regression test support. | Keep the source/configuration and tests; do not remove city folders wholesale. |
| `rss/` | 21,568,644 bytes across 16 XML files | `scripts/generate_rss.py` writes the full and latest feeds. The previous full feed is also the next build's comparison baseline; the files are published feed state. | Keep for now. These are inherited, non-Genova feeds and should be retired in a separate migration that replaces their consumers. |
| `report/` | 2,780,271 bytes across 16 files | Generated per-city JSON and HTML diagnostics, produced by `scripts/report.py`; the inherited `.gitignore` documents these pages as published on GitHub Pages. | Keep as upstream diagnostic output pending a deliberate decision about retiring those pages. |
| `docs/` | 8,444,824 bytes across 54 files | Project and upstream documentation, including screenshots used as reference material. | Keep; images are documentation, not transient test recordings. |
| `cc-architecture.mp4`, `video/event-poster-capture.mp4` | 3,884,424 bytes combined | Root-level demonstration/reference videos. | Keep; not part of this cleanup. |

## Remove: stale logs and generated browser recordings

The current tree contains 51,188,217 bytes across 567 tracked files. This PR removes 5,453,093 bytes from the current working tree:

| Paths | Size | Finding |
| --- | ---: | --- |
| `build.log` | 222,396 bytes | A tracked output snapshot, not an input to the Genova preview or current PR checks. `scripts/report.py` can read a newly generated build log when rebuilding upstream diagnostics. |
| `cities/santarosa/fuzzy_dedup.log` | 43,288 bytes | Generated run log; not needed by the regression tests or the Genova preview. |
| `cities/santarosa/traces/videos/*.webm` (10 files) | 5,187,409 bytes | Regression videos are recordings of test runs, not test fixtures or comparison baselines. The manual regression workflow will retain new recordings as a 14-day Actions artifact instead of committing them. |

The regression specs, JSON baselines, media test fixture, and test scripts remain tracked. The workflow stays manual and continues to run the inherited tests; this change only changes where its generated recordings are stored.

## Repository-size limit

Removing files from the current tree does not erase earlier copies from Git history. The repository remains larger when cloned until its history is intentionally rewritten; this routine cleanup does not rewrite public history. The RSS and report data above also remain in the current tree because the inherited feed/diagnostic consumers still exist.
