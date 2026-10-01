# Genova event categories

[`genova-taxonomy.json`](../genova-taxonomy.json) is the shared category contract for the Genova preview and event-normalization helper. The preview builds its filters and category labels from this file. Category keys are stable machine values; labels are for people.

| Public key | Label |
| --- | --- |
| `music` | Music |
| `theatre-performance` | Theatre & performance |
| `art-exhibitions` | Art & exhibitions |
| `sports` | Sports & fitness |
| `food-drink` | Food & drink |
| `festivals-markets` | Festivals & markets |
| `talks-workshops` | Talks & workshops |
| `family` | Family & kids |
| `outdoors-tours` | Outdoor & tours |
| `community-social` | Community & social |

The inherited classifier's labels are mapped explicitly in the same JSON file. One broad label may map to more than one public category; for example, `Craft / Maker` maps to art/exhibitions and festivals/markets. `Government / Civic` is an intentional exclusion from this fun-events calendar. New or unrecognized labels are preserved for review.

`date-night` is a separate tag and can coexist with any category. The normalizer reports an event as `ready`, `review`, or `excluded`; missing or invalid confidence, confidence below `0.75`, and unmapped labels require review. This helper defines an output contract; it is not yet wired to a live Genova collector or database.

Issue #1 still owns producing and publishing category-specific ICS feeds from real, approved events. No live source, backend, or feed URL is established by this taxonomy change.
