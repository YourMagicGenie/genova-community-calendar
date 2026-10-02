# Genova Fixture-only Admin Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Let the sole approved Genova admin sign in, start one remote fixture-only run, and inspect its result without scanning sources or writing public events.

**Architecture:** A static admin page uses Supabase Auth. A user-authenticated Edge Function confirms the caller's Auth UUID exists in the server-owned admin_users table, creates an agent_runs row, and dispatches a manual GitHub Actions workflow. The workflow processes only committed fictional fixtures and reports through a separate token-protected callback; service-role/secret keys stay inside Supabase Edge Functions.

**Tech Stack:** Static HTML/CSS/JavaScript, Supabase Edge Functions with Deno and @supabase/server, PostgreSQL/pgTAP, GitHub Actions, Node.js tests.

**Spec:** GitHub Issue #5; AGENT.md; docs/genova-agent-run-history.md.

## Global Constraints

- Limit the pilot to Comune di Genova and Europe/Rome.
- Fixture mode is the only supported run mode in this milestone. No discovery, real source fetch, event-table write, publication, paid provider, or schedule.
- Authorization is based on Auth UUID membership in admin_users. Never trust user_metadata, a browser-only check, or the display label YMGAdmin.
- GitHub Actions receives only the run ID and a callback credential. It never receives a Supabase secret key.
- Keep the public root and sample preview on fictional fixtures.
- Do not store the temporary password from chat or request it again. Provisioning a real account requires the owner's email and a new credential set directly in Supabase.

## Review Focus

- Anonymous callers and signed-in non-admins cannot start or inspect private runs.
- Forged user metadata cannot grant admin status.
- Only fixture mode is accepted; a fixture run scans zero sources and writes zero events.
- Missing GitHub or callback configuration fails closed and records safe error state.
- Callback requests require the separate shared callback credential and can only update a valid run once.
- No browser bundle or GitHub workflow contains a Supabase service-role/secret key.

## File Map

- supabase/migrations/: explicitly grant the minimal admin status/run-history reads required by the page.
- supabase/functions/genova-agent-run/: verify an authenticated admin, create a queued run, dispatch the manual workflow.
- supabase/functions/genova-agent-callback/: validate a callback credential and update a fixture run.
- supabase/config.toml: configure the new-key-compatible Edge Function auth wrapper.
- .github/workflows/genova-agent-fixture.yml: manually dispatched, fixture-only runner with read-only repository permissions.
- scripts/genova_agent_fixture.py and tests/fixtures/genova/: deterministic offline fixture validation.
- xmlui/admin.html, xmlui/admin.js, xmlui/admin.css: sign-in, fixture-run button, and private run history.
- tests/: authorization, callback, browser-shell, and fixture-run checks.
- AGENTS.md, README.md, docs/genova-agent-run-history.md, CHANGELOG.md: accurate setup and milestone status.

## Tasks

- [ ] Write pgTAP assertions for explicit grants and admin-only run reads; run the focused database test red, then add the additive migration and confirm green.
- [ ] Write Node tests for the run endpoint's mode/auth/admin checks and callback's constant-time credential validation/payload limits; confirm red before adding handlers.
- [ ] Write Node tests for the fixture validator proving no network fetch and no public event writes; add a manual workflow that can only run the fixture validator.
- [ ] Add the static admin page; test that it exposes no signup or admin-grant path, never loads the public preview, and gates run history behind a successful Auth session/admin check.
- [ ] Document required Supabase and GitHub secrets, owner-only account provisioning, manual fixture verification, and limits; update the changelog.
- [ ] Run the complete relevant Node, Python, SQL, Markdown-link, security, performance, and browser checks; obtain independent review before PR merge.

## Self-review

- Is the only supported runner mode fixture-only?
- Does every privileged DB write remain server-side?
- Does the fixture runner have zero source network access and zero event-store writes?
- Are setup steps clear about the missing admin email and owner-managed secrets?
