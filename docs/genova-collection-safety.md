# Genova collection: current safe state

The inherited `Generate Calendar` workflow formerly ran daily and could
process every upstream city, register pending sources, contact a Supabase
project, and push generated files and an archive branch. Issue #10 replaced
it with a **manual, read-only scope check**. The old implementation remains
in Git history for reference; it must not be re-enabled as a publisher.

The replacement has no schedule, no external API calls, no secrets, and only
read-only repository permission. It cannot scan sources or publish events.
The inherited `Generate Calendar` scope-check workflow remains disabled in
the fork's Actions settings. It is not the Issue #5 agent workflow and must not
be re-enabled as a publisher. Issue #5 adds a separate manual fixture-only
workflow; it has no source scan, schedule, or event writer.

To test locally without credentials:

```bash
python scripts/plan_genova_collection.py --scope genova --enabled-cities genova
python -m unittest discover -s tests -p 'test_plan_genova_collection.py' -v
```

The output lists `genova` with zero approved sources and both collection and
writes disabled. A missing `ENABLED_CITIES` variable, `all`, or an upstream
city fails closed. A future manual GitHub dry run requires the reviewed
repository variable `ENABLED_CITIES` to equal `genova` exactly.

There is no recurring collection cost or recovery procedure to operate yet.
The owner has selected Giardini Luzzati / Spazio Comune as the first small
external-source test. The source whitelist is owner-selected; the collector
must check robots.txt for the exact public listing path, skip any disallowed
path, and continue with other selected sources. The pilot stores event title,
date/time and location when listed, publisher name, and original event URL;
it copies no descriptions or images. If crawler instructions are unavailable
or the site explicitly blocks automated collection, skip that source for the
run without blocking the calendar. Complete the Issue #59 hosted security gate
and Issue #49 fixture run before connecting real collection to Supabase. Keep
the first source run manual and small; recurring daily refresh follows only
after basic reliability and recovery are proven. No paid provider is enabled.
