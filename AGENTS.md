# Agent guidance — Porto Aperto | Genova calendar

This is a public fork of `judell/community-calendar`. Work here is for the
Genova calendar, a free Porto Aperto feature maintained by one person. Explain
changes in ordinary language and keep PRs small enough to review on a phone.

## Start with the current project

1. Read `PROJECT_SCOPE.md` and the relevant open issue before changing code.
   Issue #1 tracks the first release; issue #5 tracks the future source agent
   and admin controls; issue #6 tracks the sample calendar review.
2. Read `docs/fork-readiness.md` for the inherited stack and its operating
   risks. The root `README.md`, `CONTRIBUTING.md`, most city directories, and
   many files under `docs/` still describe the upstream project. Treat them as
   reference material until verified for this fork.
3. When available, read the central note, Status, and relevant Decisions in
   `YourMagicGenie/Obsidian-Project-Keeper/projects/genova-community-calendar/`.
   Keep durable project changes there, while code, issues, PRs, and release
   criteria stay in this repository. Do not change the owner's priorities.

`PROJECT_SCOPE.md` defines success. An issue defines one slice of that work.
State what is implemented, what is still a fixture, and what needs owner setup.
Do not mark release criteria complete because a sample page looks finished.

## What actually works today

- The root URL and `/?city=genova` route to
  `xmlui/genova-sample-preview.html`. Its data in
  `xmlui/sample-events.json` is fictional and links only to `example.org`.
  `xmlui/sample-preview.js` and `.css` implement the month grid, category
  checkboxes, and crowded-day expansion.
- The inherited app entry at `/xmlui/` also redirects to that preview. Other
  city requests show an unconfigured message; none of these public routes load
  the inherited backend client.
- The ordinary `xmlui/` app, `cities/`, `scrapers/`, `scripts/`, and
  `supabase/` contain inherited multi-city code. They are useful starting
  points, but they do not establish a working Genova collection pipeline,
  admin panel, or calendar subscription.
- `xmlui/config.json` contains the owner-controlled Genova Supabase URL and
  publishable key. The root and Genova public preview remain isolated from
  Supabase and display fictional fixtures only. The hosted project has the
  application tables with RLS enabled, but no Auth user, approved sources, or
  events. Complete Issue #59's security review before creating the admin
  identity or running the fixture workflow; the database connection alone is
  not a live collector.
- `.github/workflows/generate-calendar.yml` is the old manual, read-only
  Genova scope check. It has no schedule, source scan, or writer, and remains
  disabled in Actions. The separate Issue #5 workflow currently validates
  fictional fixtures only after its admin and secret setup is complete. See
  `docs/genova-collection-safety.md`.

## Product rules for Genova work

- Start within the Comune di Genova. Expand to other Ligurian areas only by
  an explicit scope decision. Use `Europe/Rome` for event dates and times.
- Public browsing and category feeds remain free and account-free. Discovery,
  source approval, run controls, corrections, and troubleshooting belong to
  the authenticated maintainer area, enforced server-side.
- A discovered URL is a candidate, not permission to collect. Only sources
  explicitly approved and active in the source directory may be scanned.
  Respect publisher terms, robots/access limits, and sensible request rates;
  never bypass login walls or scrape private social content.
- Preserve original source names and event links. Record title, local date,
  time when known, venue/location, categories, and collection method. Leave
  unknown fields unknown. Flag uncertain data for review rather than inventing
  it. Keep separate showtimes, handle changes/cancellations, and prevent one
  failed source from deleting healthy sources' events.
- Keep the public calendar manageable: clear category filters, an extra Date
  night tag, compact day previews with expansion, and correct empty states.
  Align any new taxonomy with the UI, normalization, and category feeds.
- Prefer free and low-maintenance methods. Document expected recurring cost,
  limits, and the owner's decision before enabling paid APIs or scheduled
  agent runs. Never commit secrets or service-role keys.

`AGENTS.md` guides coding agents in this repository. The proposed dedicated
event-curation agent's operating contract belongs in a separate `AGENT.md`
under issue #5; that agent does not exist merely because this file exists.

## Change and review workflow

- Work one issue at a time. Check open issues before filing another and give
  each PR a focused goal, acceptance criteria, and an honest test summary.
  Use GitHub Issues and PRs as the review record; no Worklist file or Bram
  approval service is part of this fork's current setup.
- Add one short `CHANGELOG.md` entry for every PR with a reader or maintainer
  impact. If a PR needs no entry, explain why in its description. The changelog
  summarizes merged progress; Git history retains exact technical details.
- For source changes, document publisher URL, method, access conditions,
  attribution, geography, expected event types, and approval state. Keep a
  candidate separate from an active source. Test with fixtures and a dry run
  before connecting real credentials or publishing real events.
- For the sample page, run `node --test tests/sample-preview.test.js`. For
  Edge Function authorization changes, run
  `node --test tests/load-events-protection.test.mjs`. For pipeline changes,
  use Python 3.12, run the offline ICS fixture test
  (`pytest tests/test_timezone_pipeline.py::TestRealIcsFiles -v`), the full
  Python suite (`pytest tests/ -v`), and feed validation. For database changes,
  use local Supabase and `supabase test db supabase/tests/`. The PR workflow
  also checks dependency security with `pip-audit` and runs a benchmark.
  Report checks that could not run; a missing check is not a pass.
- For a visible UI or event-output PR, provide a working preview URL and
  concise phone and laptop review steps. Confirm behavior on the deployed
  page before closing a live-review issue. Keep sample data labeled until
  real sources meet the release criteria.
- Merge only after relevant automated checks pass and the PR's stated
  acceptance criteria are met. If deployment settings, credentials, or real
  device review require the maintainer, say exactly what they need to do.

## Project continuity

After a meaningful milestone, decision, validated finding, blocker, scope
change, or change in next actions, update the Project Keeper Status and, when
appropriate, Decisions with the short durable delta and a link to evidence.
Do not copy an issue backlog or routine debugging transcript into it. If
Keeper cannot be written, provide the exact update that remains to be saved.
