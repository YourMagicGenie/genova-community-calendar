# Genova category suggestions

`scripts.genova_taxonomy.suggest_categories()` is the shared, deterministic category suggester for approved Genova source adapters and bulletin parsers.

```python
from scripts.genova_taxonomy import suggest_categories

suggestions = suggest_categories(
    title="Concerto jazz e laboratorio per famiglie",
    text="Optional event text used transiently for matching.",
    section="Musica",
    venue="Optional venue name",
    structured_categories=["Music / Concerts"],
)
```

The result is an ordered list of up to three objects with a stable Genova category key, confidence from 0 to 1, and a short evidence summary. Evidence describes the signal type and does not copy publisher prose. Structured labels, section headings, titles, event text, and venues are accepted by the same API so website collectors and the PDF parser can share behavior.

When there is usable source context but no matching category cue, the suggester returns a `community-social` fallback at `0.2` confidence, explicitly marked as a low-confidence fallback. With no context it returns an empty list. Callers must keep the event in review; suggestions never approve or publish an event. `date-night` remains a separate tag and is never returned as a category.

The Luzzati collector stores suggestions on private `genova_event_facts.category_suggestions`. Admins can read the values, but only the trusted importer can write them. The separate admin-form work in issue #104 controls how a reviewer accepts or edits them. Bulletin parsing in #98 should import this helper rather than defining its own keyword rules.
