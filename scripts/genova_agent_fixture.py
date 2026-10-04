#!/usr/bin/env python3
"""Validate the checked-in fictional Genova agent fixture without network access."""

import argparse
import json
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests/fixtures/genova/agent-fixture.json"
ALLOWED_CATEGORIES = {
    "music",
    "theatre-performance",
    "art-exhibitions",
    "sports",
    "food-drink",
    "festivals-markets",
    "talks-workshops",
    "family",
    "outdoors-tours",
    "community-social",
}


def validate_fixture(fixture):
    if fixture.get("fictional") is not True:
        raise ValueError("fixture must be explicitly fictional")
    candidates = fixture.get("candidates")
    events = fixture.get("events")
    if not isinstance(candidates, list) or not isinstance(events, list) or not events:
        raise ValueError("fixture must contain candidate and event lists")
    for candidate in candidates:
        if not candidate.get("name") or not candidate.get("url", "").startswith("https://example.org/"):
            raise ValueError("fixture candidates must use example.org links")
    for event in events:
        if event.get("fictional") is not True:
            raise ValueError("every fixture event must be explicitly fictional")
        if event.get("city") != "genova":
            raise ValueError("fixture event city must be genova")
        if not event.get("title") or not event.get("source_url", "").startswith("https://example.org/"):
            raise ValueError("fixture events need a title and example.org source link")
        date.fromisoformat(event["date"])
        if event.get("timezone") != "Europe/Rome":
            raise ValueError("fixture event timezone must be Europe/Rome")
        if not event.get("categories") or not set(event["categories"]).issubset(ALLOWED_CATEGORIES):
            raise ValueError("fixture event categories must use the Genova taxonomy")
        if not isinstance(event.get("confidence"), (int, float)) or not 0 <= event["confidence"] <= 1:
            raise ValueError("fixture event confidence must be between zero and one")
    needs_review = sum(1 for event in events if event["confidence"] < 0.6)
    return {
        "candidate_count": len(candidates),
        "sources_scanned": 0,
        "events_found": len(events),
        "events_needing_review": needs_review,
        "events_added": 0,
        "events_updated": 0,
        "events_cancelled": 0,
        "source_failures": [],
    }


def load_fixture():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return validate_fixture(fixture)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print a compact result for the admin run callback")
    args = parser.parse_args()
    try:
        result = load_fixture()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("Genova fixture check passed; no sources scanned and no events written.")
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
