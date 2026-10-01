# Genova collection: current safe state

The inherited `Generate Calendar` workflow formerly ran daily and could
process every upstream city, register pending sources, contact a Supabase
project, and push generated files and an archive branch. Issue #10 replaced
it with a **manual, read-only scope check**. The old implementation remains
in Git history for reference; it must not be re-enabled as a publisher.

The replacement has no schedule, no external API calls, no secrets, and only
read-only repository permission. It cannot scan sources or publish events.
The GitHub workflow is still disabled in the fork's Actions settings; leave
it disabled until the subsequent Genova source and backend reviews are done.

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
Before enabling a schedule or live publisher, the maintainer must review
source access and approval (#5, #13), a fork-owned backend (#11), writer
authorization (#12), expected service costs and quotas, failure recovery,
and a working no-credentials dry run. A new workflow should only read active,
approved Genova sources and never use inherited city data or upstream keys.
