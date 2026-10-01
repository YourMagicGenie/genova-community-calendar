# Porto Aperto | Genova calendar

Porto Aperto is building a free, easy-to-browse calendar that brings together
public events around Genova. The project starts in Genova and aims to combine
useful event listings from local publishers, venues, and organizations.

## Try the preview

[Open the Genova calendar preview](https://yourmagicgenie.github.io/genova-community-calendar/).

The page currently shows **fictional sample events only**. It has no live event
feed, approved publisher list, admin panel, automated collector, or configured
database. The preview demonstrates the calendar layout and controls; it does
not yet show what is happening in Genova.

## Project scope and source approval

- Read [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for the launch goal and success
  criteria.
- The future source-discovery agent and admin approval process are described in
  [issue #5](https://github.com/YourMagicGenie/genova-community-calendar/issues/5).
- [Suggest a public event source](https://github.com/YourMagicGenie/genova-community-calendar/issues/new?template=add-feed.md).
  A suggestion is a candidate for review. It does not add or activate a source.
- See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing code or source
  changes.

Only public sources that the maintainer has explicitly approved may be scanned.
Submissions should include access conditions and attribution details. Do not
submit private links, credentials, or instructions to get around a login wall.

## Run the preview and tests

Use Python to serve the static preview from the repository root:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/?city=genova&preview=sample>. The sample page
does not need a database or API keys.

Run the preview and writer-security tests with Node.js 20 or newer:

```bash
node --test tests/sample-preview.test.js tests/load-events-protection.test.mjs
```

The pull request checks also run Python tests and local Supabase database tests.
Those inherited pipeline and database components are not a configured Genova
collection service.

## About the upstream project

This repository is a fork of
[judell/community-calendar](https://github.com/judell/community-calendar),
licensed under Apache 2.0. The upstream project supplied useful code and ideas;
this fork adapts them for Porto Aperto and Genova. Keep the upstream copyright
and license notices in place.

Many inherited technical documents still describe the upstream multi-city
system. Treat them as reference material until specifically adapted for this
project. This includes `docs/pipeline.md`, `docs/curator-guide.md`,
`docs/procedures.md`, `scrapers/README.md`, and parts of `supabase/README.md`.
For the current project state, use `PROJECT_SCOPE.md`, `AGENTS.md`, and
`docs/fork-readiness.md`.
