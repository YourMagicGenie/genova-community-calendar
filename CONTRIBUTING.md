# Contributing to Porto Aperto | Genova calendar

This fork is being adapted for events in Genova. The public page is currently a
fictional sample preview; it does not yet collect or publish real events.
Read [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for the goal and release criteria.

## Suggest a source

Use the [event source request form](https://github.com/YourMagicGenie/genova-community-calendar/issues/new?template=add-feed.md)
to propose a public calendar, events page, venue, or local publisher. Include
the source's public URL, geography, likely event types, access conditions, and
how the source should be credited.

Every source begins as a proposal. A maintainer reviews whether it fits the
project, can be accessed respectfully, and provides useful Genova events. A
merged pull request, issue submission, or AI discovery result does not approve
or activate a source. The future admin and source approval workflow is tracked
in [issue #5](https://github.com/YourMagicGenie/genova-community-calendar/issues/5).

Do not submit private URLs, login credentials, or content that requires an
account. Do not bypass publisher access controls or ignore stated terms and
request limits. Preserve the publisher's name and original event link.

## Propose code or documentation

1. Open or find a GitHub issue describing the change. Keep a pull request
   focused on one issue.
2. Follow the repository's [AGENTS.md](AGENTS.md) and current
   [project scope](PROJECT_SCOPE.md). Do not treat upstream-only instructions
   as live Genova configuration.
3. Run the checks that match your change:

   ```bash
   node --test tests/sample-preview.test.js tests/load-events-protection.test.mjs
   python scripts/check_markdown_links.py
   ```

   The PR workflow also runs Python tests and local Supabase database tests.
   Note any check you could not run; a missing check is not a pass.
4. Add a short reader-facing entry to `CHANGELOG.md` for each PR, or explain in
   the PR description why a change does not warrant one.
5. In the PR description, state what changed, how it was checked, and anything
   that still needs maintainer setup or review.

Keep sample data visibly fictional. Do not commit API keys, database secrets,
or private event data. Do not enable a collector or connect a database without
the maintainer's explicit setup and source approval.

## Scope discussion

The active project area is Genova. To discuss a future expansion elsewhere in
Liguria, use the [area proposal form](https://github.com/YourMagicGenie/genova-community-calendar/issues/new?template=add-city-or-aggregator.md).
An area proposal starts a discussion; it does not change the project's scope.

## Upstream attribution

The repository is a fork of
[judell/community-calendar](https://github.com/judell/community-calendar) and
retains its Apache 2.0 license and copyright notices. Many inherited technical
documents describe upstream behavior rather than a working Genova system; see
the README's [reference-document note](README.md#about-the-upstream-project).
