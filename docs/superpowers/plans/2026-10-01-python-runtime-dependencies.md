# Python Runtime and Dependencies Implementation Plan

> **For agentic workers:** Use the implementation plan task by task and verify each change in GitHub Actions before merging.

**Goal:** Establish one supported Python runtime for the inherited pipeline and make direct dependency installs reproducible.

**Architecture:** Declare Python 3.12 consistently in the repository, workflows, and local build guide. Exact-pin production and test dependencies, then run the real ICS fixture tests and full PR validation. No live sources, credentials, or collection schedule are introduced.

**Tech Stack:** Python 3.12, pip, pytest, GitHub Actions.

**Spec:** GitHub Issue #19.

## Global Constraints

- Keep public browsing fixture-only and source collection disabled.
- Preserve practical upstream parser compatibility.
- Use the same Python 3.12 minor series in local instructions and workflow setup.

## Review Focus

- Native XML dependency install on Python 3.12: verify clean pip install and import.
- iCalendar and recurrence API compatibility: run the offline ICS fixture tests.
- Existing Genova dry-run safety: run its no-network tests as part of the Python suite.
- Local instructions and all Python-using workflows: verify they match the declared runtime.

---

### Task 1: Runtime and direct dependency pins

**Files:** `.python-version`, `requirements.txt`, `requirements-dev.txt`.

- [x] Set Python 3.12 as the supported runtime.
- [ ] Replace open-ended direct dependency ranges and stale pins with tested exact versions.

### Task 2: CI and maintainer instructions

**Files:** `.github/workflows/validate-pr.yml`, `.github/workflows/generate-calendar.yml`, `docs/local-build.md`.

- [x] Align Python setup with 3.12.
- [ ] Document install, offline fixture test, and supported runtime.

### Task 3: Verification

- [ ] Run dependency audit, the offline ICS fixture tests, and the full Python suite under Python 3.12.
- [ ] Record clean install/test results and review dependency security/update cadence.
